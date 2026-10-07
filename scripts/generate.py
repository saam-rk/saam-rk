"""Run with --refresh for live public data, or offline from the committed snapshot."""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .artwork import render_all
from .data import fetch_snapshot, validate_days

ROOT = Path(__file__).resolve().parents[1]


def validate_config(config):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", config["username"]):
        raise ValueError("Invalid GitHub username")
    if not 320 <= config["width"] <= 1680:
        raise ValueError("Width must be between 320 and 1680")
    if not 0.1 <= config["motion_seconds"] <= 20:
        raise ValueError("Animation duration must be between 0.1 and 20 seconds")
    if len(config["tagline"]) > 60:
        raise ValueError("Keep the tagline under 61 characters")
    colors = config["colors"]
    for color in [colors[key] for key in ("background", "panel", "border", "text", "muted", "accent")] + colors["heat"]:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Colors must be six-digit hex values")
    if len(colors["heat"]) != 5:
        raise ValueError("The contribution palette needs five levels")


def write_changed(path, content):
    encoded = content.encode("utf-8")
    if path.exists() and path.read_bytes() == encoded:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    print(f"Updated {path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Fetch current public GitHub data")
    args = parser.parse_args()
    try:
        config = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
        validate_config(config)
        snapshot_path = ROOT / "data/profile.json"
        snapshot = (fetch_snapshot(config["username"], datetime.now(timezone.utc).date())
                    if args.refresh else json.loads(snapshot_path.read_text(encoding="utf-8")))
        if snapshot["username"].lower() != config["username"].lower():
            raise ValueError("Snapshot username differs from configuration; use --refresh")
        validate_days(snapshot["days"])
        # Fetch and validate everything before touching the last successful output.
        assets = render_all(config, snapshot)
        if args.refresh:
            write_changed(snapshot_path, json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
        for name, source in assets.items():
            write_changed(ROOT / "assets" / name, source)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(f"Generation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
