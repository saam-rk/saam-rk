"""Deterministic SVG renderers. All coordinates use an 840-unit design canvas."""
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, timedelta
from html import escape


def text(x, y, value, size=16, fill="text", extra=""):
    return (f'<text x="{x}" y="{y}" font-size="{size}" class="{fill}" {extra}>'
            f'{escape(str(value))}</text>')


def svg(config, title, description, height, body):
    colors = config["colors"]
    duration = config["motion_seconds"]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{config['width']}" height="{round(height * config['width'] / 840)}" viewBox="0 0 840 {height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title>
<desc id="desc">{escape(description)}</desc>
<style>
text {{ font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace; }}
.text {{ fill: {colors['text']}; }} .muted {{ fill: {colors['muted']}; }} .accent {{ fill: {colors['accent']}; }}
.reveal {{ animation: reveal {duration}s ease-out both; }}
.trace {{ stroke-dasharray: 8 12; animation: trace {duration}s linear 3; }}
.cursor {{ animation: cursor 1.2s step-end 4; }}
@keyframes reveal {{ from {{ opacity: .7; }} to {{ opacity: 1; }} }}
@keyframes trace {{ to {{ stroke-dashoffset: -80; }} }}
@keyframes cursor {{ 50% {{ opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .reveal, .trace, .cursor {{ animation: none !important; }} }}
</style>
<rect x="1" y="1" width="838" height="{height - 2}" rx="14" fill="{colors['background']}" stroke="{colors['border']}"/>
{body}
</svg>
'''


def header(config, _snapshot):
    c = config["colors"]
    body = text(32, 38, "~/" + config["username"], 14, "muted")
    body += text(808, 38, "PUBLIC WORKSPACE", 12, "muted", 'text-anchor="end"')
    body += text(32, 111, config["username"], 58, extra='font-weight="700" letter-spacing="-3"')
    body += f'<path class="trace" d="M 390 96 H 800" stroke="{c["accent"]}" opacity=".45"/>'
    body += text(34, 152, config["tagline"], 18, "muted")
    body += f'<rect class="cursor" x="34" y="178" width="10" height="4" fill="{c["accent"]}"/>'
    return svg(config, config["username"], config["tagline"], 208, body)


def terminal(config, snapshot):
    repos = [repo for repo in snapshot["repositories"]
             if not repo["fork"] and repo["name"].lower() != config["username"].lower()]
    languages = Counter(repo["language"] for repo in repos if repo["language"])
    ranked = sorted(languages, key=lambda name: (-languages[name], name))[:3]
    names = {repo["name"] for repo in repos}
    stack = [item["name"] for item in config["technologies"] if item["repo"] in names]
    rows = [
        ("user", snapshot["username"]),
        ("languages", " / ".join(ranked) or "Not reported"),
        ("repo stack", " / ".join(stack) or "Not configured"),
        ("public repos", str(snapshot["public_repos"])),
        ("followers", str(snapshot["followers"])),
        ("repo stars", str(sum(repo["stargazers_count"] for repo in repos))),
    ]
    body = text(32, 38, "$ profile --public", 16, "accent")
    body += text(808, 38, snapshot["as_of"], 12, "muted", 'text-anchor="end"')
    body += f'<path d="M32 58 H808" stroke="{config["colors"]["border"]}"/>'
    for index, (label, value) in enumerate(rows):
        y = 94 + index * 32
        body += f'<g class="reveal" style="animation-delay:{index * .08:.2f}s">'
        body += text(32, y, label, 16, "muted") + text(218, y, value, 18) + '</g>'
    body += text(32, 294, "Languages: top language per original public project.", 13, "muted")
    return svg(config, "Public repository snapshot", "; ".join(f"{k}: {v}" for k, v in rows), 318, body)


def visual(config, _snapshot):
    c = config["colors"]
    body = text(32, 36, "$ make something-useful", 14, "muted")
    body += f'<path d="M170 99 H674" stroke="{c["border"]}" stroke-width="2"/>'
    body += f'<path class="trace" d="M170 99 H674" stroke="{c["accent"]}" stroke-width="2"/>'
    for x, label, glyph in ((138, "source", "{ }"), (390, "build", ">_"), (642, "output", "[+]")):
        body += f'<rect x="{x}" y="66" width="60" height="64" rx="8" fill="{c["panel"]}" stroke="{c["border"]}"/>'
        body += text(x + 30, 106, glyph, 22, "accent", 'text-anchor="middle"')
        body += text(x + 30, 157, label, 14, "muted", 'text-anchor="middle"')
    return svg(config, "Source to build to output", "An abstract terminal pipeline; not a portrait or a live build status.", 182, body)


def contributions(config, snapshot):
    days = snapshot["days"]
    total = sum(day["count"] for day in days)
    active = sum(day["count"] > 0 for day in days)
    first = date.fromisoformat(days[0]["date"])
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    last = date.fromisoformat(days[-1]["date"])
    columns = (last - start).days // 7 + 1
    step = min(14, 738 / columns)
    body = text(32, 36, "$ activity --calendar", 16, "accent")
    body += text(32, 64, f'{days[0]["date"]} / {days[-1]["date"]}', 13, "muted")
    for row, label in ((1, "M"), (3, "W"), (5, "F")):
        body += text(32, 106 + row * 17, label, 11, "muted")
    for day in days:
        current = date.fromisoformat(day["date"])
        col, row = divmod((current - start).days, 7)
        x, y = 64 + col * step, 96 + row * 17
        color = config["colors"]["heat"][day["level"]]
        label = f'{day["date"]}: {day["count"]} contributions'
        body += (f'<rect class="reveal" x="{x:.2f}" y="{y}" width="{step - 3:.2f}" height="13" rx="2" '
                 f'fill="{color}" style="animation-delay:{col * .012:.3f}s"><title>{label}</title></rect>')
    body += text(32, 242, f"{total:,} contributions / {active} active days", 17)
    body += text(32, 269, "Publicly visible calendar / refreshed " + snapshot["as_of"], 12, "muted")
    body += text(653, 266, "less", 11, "muted")
    for i, color in enumerate(config["colors"]["heat"]):
        body += f'<rect x="{688 + i * 16}" y="256" width="12" height="12" rx="2" fill="{color}"/>'
    body += text(773, 266, "more", 11, "muted")
    return svg(config, "GitHub contribution calendar", f"{total} contributions across {active} active days. {days[0]['date']} to {days[-1]['date']}. Counts reflect GitHub's publicly visible calendar, not necessarily public-repository-only activity.", 290, body)


def validate_svg(source):
    root = ET.fromstring(source)
    namespace = "{http://www.w3.org/2000/svg}"
    allowed = {"svg", "title", "desc", "style", "rect", "text", "path", "g"}
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
    result = {name + ".svg": renderer(config, snapshot) for name, renderer in (
        ("header", header), ("terminal", terminal), ("visual", visual), ("contributions", contributions)
    )}
    for source in result.values():
        validate_svg(source)
    return result
