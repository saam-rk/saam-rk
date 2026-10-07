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
        for name, source in first.items():
            self.assertEqual(source, (ROOT / "assets" / name).read_text(encoding="utf-8"))
            artwork.validate_svg(source)
            self.assertIn("prefers-reduced-motion", source)
            self.assertNotIn("@import", source)
            self.assertNotIn("url(", source)

    def test_readme_relative_paths(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assets = re.findall(r'<img src="([^"]+)"[^>]+alt="[^"]+"', readme)
        self.assertEqual(len(assets), 4)
        for relative in assets + ["CUSTOMIZE.md"]:
            self.assertTrue((ROOT / relative).is_file(), relative)
        self.assertNotIn("<svg", readme)
        self.assertNotIn("<script", readme)

    def test_live_snapshot_is_valid(self):
        data.validate_days(self.snapshot["days"])
        self.assertEqual(self.snapshot["username"], self.config["username"])
        self.assertEqual(self.snapshot["public_repos"], len(self.snapshot["repositories"]))

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
        self.assertIn("0 contributions / 0 active days", svg)
        self.assertIn("2024-02-29", svg)

    def test_text_is_escaped(self):
        config = dict(self.config, tagline='<script>alert("x")</script> & text')
        source = artwork.header(config, self.snapshot)
        artwork.validate_svg(source)
        self.assertNotIn("<script>", source)
        self.assertIn("&lt;script&gt;", source)

    def test_config_rejects_unsafe_style(self):
        config = copy.deepcopy(self.config)
        config["colors"]["accent"] = 'red; background:url(https://example.com)'
        with self.assertRaises(ValueError):
            generate.validate_config(config)

    def test_profile_and_forks_do_not_inflate_project_stats(self):
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["repositories"] += [
            {"name": self.config["username"], "fork": False, "language": "Fiction", "stargazers_count": 999},
            {"name": "forked", "fork": True, "language": "Fiction", "stargazers_count": 999},
        ]
        svg = artwork.terminal(self.config, snapshot)
        self.assertNotIn("Fiction", svg)
        self.assertNotIn("1998", svg)

    def test_api_pagination(self):
        repo = {"name": "sample", "language": "Python", "fork": False,
                "stargazers_count": 0, "html_url": "https://github.com/saam-rk/sample",
                "private": False, "owner": {"login": "saam-rk"}}
        days = sample_days()
        responses = [json.dumps({"login": "saam-rk", "followers": 3}),
                     json.dumps([dict(repo, name=f"r{i}") for i in range(100)]),
                     json.dumps([repo]), calendar_html(days)]
        with patch.object(data, "request", side_effect=responses) as request:
            result = data.fetch_snapshot("saam-rk", date.fromisoformat(days[-1]["date"]))
        self.assertEqual(result["public_repos"], 101)
        self.assertIn("page=2", request.call_args_list[2].args[0])

    def test_network_failure_preserves_outputs(self):
        with patch.object(sys, "argv", ["generate.py", "--refresh"]), \
                patch.object(generate, "fetch_snapshot", side_effect=RuntimeError("unavailable")), \
                patch.object(generate, "write_changed") as write:
            self.assertEqual(generate.main(), 1)
            write.assert_not_called()

    def test_no_token_sent_to_calendar(self):
        with patch.dict(data.os.environ, {"GITHUB_TOKEN": "test-only"}), \
                patch.object(data, "urlopen") as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b"ok"
            data.request("https://github.com/users/saam-rk/contributions")
            self.assertNotIn("Authorization", dict(open_url.call_args.args[0].header_items()))
            data.request("https://api.github.com/users/saam-rk")
            self.assertEqual(open_url.call_args.args[0].get_header("Authorization"), "Bearer test-only")

    def test_disallowed_url(self):
        with self.assertRaises(ValueError):
            data.request("file:///etc/passwd")


if __name__ == "__main__":
    unittest.main()
