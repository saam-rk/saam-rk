import copy
import json
import re
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from scripts import artwork, data, generate

ROOT = Path(__file__).resolve().parents[1]


def sample_days():
    start = date(2025, 1, 5)
    return [{"date": (start + timedelta(days=i)).isoformat(), "count": 0, "level": 0}
            for i in range(365)]


def calendar_html(days):
    return "".join(
        f'<td data-date="{day["date"]}" id="d{i}" data-level="{day["level"]}"></td>'
        f'<tool-tip for="d{i}">{"No" if not day["count"] else format(day["count"], ",")} '
        'contributions on January 1st.</tool-tip>'
        for i, day in enumerate(days)
    )


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        cls.snapshot = json.loads((ROOT / "data/profile.json").read_text(encoding="utf-8"))

    def test_committed_assets_match_deterministic_render(self):
        first = artwork.render_all(self.config, self.snapshot)
        self.assertEqual(first, artwork.render_all(self.config, self.snapshot))
        self.assertEqual(set(first), {"activity.svg"})
        self.assertEqual({path.name for path in (ROOT / "assets").glob("*.svg")}, set(first))
        for name, source in first.items():
            self.assertEqual(source, (ROOT / "assets" / name).read_text(encoding="utf-8"))
            artwork.validate_svg(source)
            self.assertIn("prefers-reduced-motion", source)
            self.assertNotIn("@import", source)
            self.assertNotIn("url(", source)

    def test_readme_relative_paths(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assets = re.findall(r'<img src="([^"]+)"[^>]+alt="[^"]+"', readme)
        self.assertEqual(assets, ["assets/activity.svg"])
        self.assertIn('src="assets/activity.svg" width="100%"', readme)
        self.assertNotRegex(readme, r'<img[^>]+height=')
        self.assertNotIn("assets/contributions.svg", readme)
        for relative in assets + ["CUSTOMIZE.md"]:
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertNotIn("<svg", readme)
        self.assertNotIn("<script", readme)

    def test_live_snapshot_is_valid(self):
        data.validate_days(self.snapshot["days"])
        self.assertEqual(self.snapshot["username"], self.config["username"])
        self.assertEqual(set(self.snapshot), {"username", "as_of", "calendar_source", "days"})

    def test_parser_counts_and_attribute_order(self):
        days = sample_days()
        days[10].update(count=1234, level=4)
        parser = data.CalendarParser()
        parser.feed(calendar_html(list(reversed(days))))
        self.assertEqual(parser.days(), days)

    def test_parser_rejects_changed_markup(self):
        for source in ("<html>Rate limited</html>", calendar_html(sample_days()).replace("No contributions", "Activity")):
            with self.subTest(source=source[:40]), self.assertRaises(ValueError):
                parser = data.CalendarParser()
                parser.feed(source)
                parser.days()

    def test_invalid_calendar_data(self):
        cases = []
        missing = sample_days()
        del missing[42]
        cases.append(missing)
        duplicate = sample_days()
        duplicate[2] = duplicate[1]
        cases.append(duplicate)
        for change in ({"count": -1}, {"level": 5}, {"count": 2, "level": 0}):
            days = sample_days()
            days[3].update(change)
            cases.append(days)
        for days in cases:
            with self.subTest(days=days[3]), self.assertRaises(ValueError):
                data.validate_days(days)

    def test_zero_activity_and_leap_day(self):
        days = [{"date": (date(2024, 1, 1) + timedelta(days=i)).isoformat(), "count": 0, "level": 0}
                for i in range(366)]
        data.validate_days(days)
        snapshot = dict(self.snapshot, days=days)
        svg = artwork.contributions(self.config, snapshot)
        artwork.validate_svg(svg)
        self.assertTrue(all(count == 0 for _, count in artwork.weekly_totals(days)))
        self.assertIn("2024-02-26: 0", svg)
        days[59].update(count=3, level=1)
        self.assertEqual(dict(artwork.weekly_totals(days))[date(2024, 2, 26)], 3)

    def test_text_is_escaped(self):
        snapshot = dict(self.snapshot, username='<script>alert("x")</script> & text')
        source = artwork.contributions(self.config, snapshot)
        artwork.validate_svg(source)
        self.assertNotIn("<script>", source)
        self.assertIn("&lt;script&gt;", source)

    def test_config_rejects_unsafe_style(self):
        config = copy.deepcopy(self.config)
        config["ink"] = 'red; background:url(https://example.com)'
        with self.assertRaises(ValueError):
            generate.validate_config(config)

    def test_weekly_totals_preserve_counts_and_partial_weeks(self):
        days = sample_days()
        days[0].update(count=2, level=1)  # Sunday: its own partial week.
        days[1].update(count=5, level=1)
        days[7].update(count=3, level=1)
        weeks = dict(artwork.weekly_totals(days))
        self.assertEqual(weeks[date(2024, 12, 30)], 2)
        self.assertEqual(weeks[date(2025, 1, 6)], 8)
        self.assertEqual(sum(weeks.values()), 10)
        self.assertTrue(all(monday.weekday() == 0 for monday in weeks))

    def test_fetch_collects_only_calendar(self):
        days = sample_days()
        with patch.object(data, "request", return_value=calendar_html(days)) as request:
            result = data.fetch_snapshot("saam-rk", date.fromisoformat(days[-1]["date"]))
        request.assert_called_once_with("https://github.com/users/saam-rk/contributions")
        self.assertEqual(result["days"], days)
        self.assertEqual(set(result), {"username", "as_of", "calendar_source", "days"})

    def test_stale_calendar_rejected(self):
        with patch.object(data, "request", return_value=calendar_html(sample_days())), self.assertRaises(ValueError):
            data.fetch_snapshot("saam-rk", date(2026, 2, 1))

    def test_trace_has_no_panels_or_labels(self):
        svg = artwork.contributions(self.config, self.snapshot)
        self.assertEqual(svg.count("<path "), 1)
        self.assertIn('vector-effect="non-scaling-stroke"', svg)
        self.assertIn(f'viewBox="0 0 {self.config["width"]} {self.config["height"]}"', svg)
        self.assertNotIn("<rect", svg)
        self.assertNotIn("<text", svg)
        self.assertNotIn("infinite", svg)
        points = re.findall(r"[ML]([\d.]+),([\d.]+)", svg)
        self.assertEqual(len(points), len(artwork.weekly_totals(self.snapshot["days"])))
        for x, y in points:
            self.assertTrue(0 <= float(x) <= self.config["width"])
            self.assertTrue(0 <= float(y) <= self.config["height"])

    def test_network_failure_preserves_outputs(self):
        with patch.object(sys, "argv", ["generate.py", "--refresh"]), \
                patch.object(generate, "fetch_snapshot", side_effect=RuntimeError("unavailable")), \
                patch.object(generate, "write_changed") as write:
            self.assertEqual(generate.main(), 1)
            write.assert_not_called()

    def test_no_token_sent_to_calendar(self):
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test-only"}), \
                patch.object(data, "urlopen") as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b"ok"
            data.request("https://github.com/users/saam-rk/contributions")
            self.assertNotIn("Authorization", dict(open_url.call_args.args[0].header_items()))

    def test_disallowed_url(self):
        for url in ("file:///etc/passwd", "https://api.github.com/users/saam-rk",
                    "https://github.com.evil.test/users/saam-rk/contributions"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                data.request(url)


if __name__ == "__main__":
    unittest.main()
