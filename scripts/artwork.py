"""A single, transparent activity trace. No cards, labels, or decorative data."""
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from html import escape


def weekly_totals(days):
    weeks = {}
    for day in days:
        current = date.fromisoformat(day["date"])
        monday = current - timedelta(days=current.weekday())
        weeks[monday] = weeks.get(monday, 0) + day["count"]
    return sorted(weeks.items())


def contributions(config, snapshot):
    weeks = weekly_totals(snapshot["days"])
    width, height = config["width"], config["height"]
    padding = 3
    peak = max(1, max(count for _, count in weeks))
    points = []
    for index, (_, count) in enumerate(weeks):
        x = padding + index * (width - 2 * padding) / max(1, len(weeks) - 1)
        y = height - padding - count / peak * (height - 2 * padding)
        points.append(f'{"M" if index == 0 else "L"}{x:.2f},{y:.2f}')
    description = (
        f'{snapshot["username"]}: weekly contribution totals, '
        f'{snapshot["days"][0]["date"]} to {snapshot["days"][-1]["date"]}. '
        'Oldest to newest; linear scale from zero to the highest weekly total. '
        'Boundary weeks may be partial. Counts reflect the publicly visible GitHub '
        'calendar, which may include anonymized private activity. '
        + '; '.join(f'{monday.isoformat()}: {count}' for monday, count in weeks)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">Weekly GitHub activity</title>
<desc id="desc">{escape(description)}</desc>
<style>
.trace {{ animation: draw {config['motion_seconds']}s ease-out both; }}
@keyframes draw {{ from {{ stroke-dashoffset: 1; }} to {{ stroke-dashoffset: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .trace {{ animation: none; }} }}
</style>
<path class="trace" d="{' '.join(points)}" fill="none" stroke="{config['ink']}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" pathLength="1" stroke-dasharray="1"/>
</svg>
'''


def validate_svg(source):
    root = ET.fromstring(source)
    namespace = "{http://www.w3.org/2000/svg}"
    allowed = {"svg", "title", "desc", "style", "path"}
    if root.tag != namespace + "svg" or not root.get("viewBox"):
        raise ValueError("Expected a scalable SVG document")
    for element in root.iter():
        if element.tag.removeprefix(namespace) not in allowed:
            raise ValueError(f"Unexpected SVG element: {element.tag}")
        for attribute in element.attrib:
            if attribute.lower().startswith("on") or "href" in attribute.lower():
                raise ValueError("Scripts and external SVG resources are forbidden")
    if root.find(namespace + "title") is None or root.find(namespace + "desc") is None:
        raise ValueError("SVG must include accessible title and description")


def render_all(config, snapshot):
    source = contributions(config, snapshot)
    validate_svg(source)
    return {"contributions.svg": source}
