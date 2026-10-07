"""Public GitHub metadata and anonymous contribution calendar; standard library only."""
import json
import os
import re
import time
from datetime import date, timedelta
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(url: str) -> str:
    if not url.startswith(("https://api.github.com/", "https://github.com/users/")):
        raise ValueError("Only GitHub HTTPS endpoints are permitted")
    headers = {"User-Agent": "github-profile-svg", "Accept-Language": "en-US"}
    # Never send credentials to the public HTML endpoint.
    if url.startswith("https://api.github.com/"):
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                return response.read().decode("utf-8")
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"GitHub request failed: HTTP {error.code}") from None
        except (URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError("GitHub request failed after three attempts") from None
        time.sleep(2 ** attempt)
    raise RuntimeError("GitHub request exhausted retries")


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.tips = {}
        self.current_tip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs:
            key = attrs.get("id")
            day = attrs.get("data-date")
            level = attrs.get("data-level")
            if key is None or day is None or level is None:
                raise ValueError("Incomplete contribution cell")
            if key in self.cells:
                raise ValueError("Duplicate contribution cell")
            self.cells[key] = (day, int(level))
        if tag == "tool-tip":
            self.current_tip = attrs.get("for")
            self.tips[self.current_tip] = ""

    def handle_data(self, data):
        if self.current_tip is not None:
            self.tips[self.current_tip] += data

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.current_tip = None

    def days(self):
        result = []
        for key, (day, level) in self.cells.items():
            tip = self.tips.get(key, "").strip()
            match = re.match(r"(No|[\d,]+) contributions? on\b", tip)
            if not match:
                raise ValueError(f"Missing or unrecognized contribution count for {day}")
            count = 0 if match[1] == "No" else int(match[1].replace(",", ""))
            if not 0 <= level <= 4 or (count == 0) != (level == 0):
                raise ValueError(f"Invalid contribution level/count for {day}")
            result.append({"date": day, "count": count, "level": level})
        result.sort(key=lambda item: item["date"])
        validate_days(result)
        return result


def validate_days(days):
    if not 350 <= len(days) <= 371:
        raise ValueError("Expected approximately one year of contribution cells")
    previous = None
    for day in days:
        current = date.fromisoformat(day["date"])
        if previous is not None and current != previous + timedelta(days=1):
            raise ValueError("Contribution calendar contains missing or duplicate dates")
        if type(day["count"]) is not int or day["count"] < 0:
            raise ValueError("Invalid contribution count")
        if type(day["level"]) is not int or not 0 <= day["level"] <= 4:
            raise ValueError("Invalid contribution level")
        if (day["count"] == 0) != (day["level"] == 0):
            raise ValueError("Contribution count/level mismatch")
        previous = current


def fetch_snapshot(username, today):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", username):
        raise ValueError("Invalid GitHub username")
    base = f"https://api.github.com/users/{username}"
    user = json.loads(request(base))
    repos = []
    page = 1
    while True:
        batch = json.loads(request(f"{base}/repos?type=owner&per_page=100&page={page}"))
        for repo in batch:
            if repo["private"] or repo["owner"]["login"].lower() != username.lower():
                continue
            repos.append({key: repo[key] for key in (
                "name", "language", "fork", "stargazers_count", "html_url"
            )})
        if len(batch) < 100:
            break
        page += 1
    calendar = CalendarParser()
    calendar.feed(request(f"https://github.com/users/{username}/contributions"))
    days = calendar.days()
    if date.fromisoformat(days[-1]["date"]) not in (today, today - timedelta(days=1)):
        raise ValueError("GitHub returned a stale contribution calendar")
    return {
        "username": user["login"],
        "as_of": today.isoformat(),
        "public_repos": len(repos),
        "followers": user["followers"],
        "repositories": sorted(repos, key=lambda repo: repo["name"].lower()),
        "calendar_source": f"https://github.com/users/{username}/contributions",
        "days": days,
    }
