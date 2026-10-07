# Customization

The profile is intentionally text-first: three project links and one small activity trace beneath them. No cards, calendar grid, stack lists, counters, or external widgets.

`assets/activity.svg` is a transparent line graph on an 840 × 64 canvas. It fills the README's available width and scales its height proportionally; the stroke stays thin and readable at every size. Its filename is deliberately different from the former calendar asset, avoiding reuse of that image's cached URL.

- **Words and projects:** edit `README.md`. Descriptions come from the linked public repositories; SWODS remains explicitly a prototype.
- **Size, color, speed:** edit `width`, `height`, `ink`, and `motion_seconds` in `profile.json`. The README image uses `width="100%"`; change the canvas dimensions to adjust its proportions rather than fixing its display height. The SVG has a transparent background and a neutral stroke for both GitHub themes.
- **Displayed data:** `weekly_totals()` in `scripts/artwork.py` groups the calendar by Monday-start weeks. The trace draws once, never loops, respects reduced motion, and stays visible without animation support.

Python 3.11+; no packages to install. From the repository root:

```sh
python -m scripts.generate            # regenerate from the committed snapshot
python -m scripts.generate --refresh  # fetch current data and regenerate
python -m unittest discover -s tests -v
```

## Activity data

The small line shows weekly contribution totals from oldest to newest. Height is linear, from zero to the largest weekly total in the displayed period. First and last weeks may be partial. A quiet week is zero, not missing data. Exact dates and daily counts are in `data/profile.json`; the SVG description also contains the weekly totals.

The source is GitHub's anonymous [public calendar](https://github.com/users/saam-rk/contributions), fetched without tokens. GitHub may include anonymized private activity if enabled on the profile, so this is not a public-repositories-only count. No private repository details, follower counts, language rankings, or technology lists are collected.

Generation validates dates, counts, and freshness before writing. Failed requests or changed HTML stop the update rather than replacing real data with zeros. The last committed image stays available. Identical inputs produce identical output.

## Automation

GitHub Actions uses Python 3.13 and SHA-pinned actions. It refreshes at **06:23 UTC daily**, manually, and on generator/config changes to `main`. Only the main-branch update job has `contents: write`; it commits changed generated files using the built-in token. Pull requests run offline checks with read-only permissions and never publish.

No secrets need configuring. GitHub may delay schedules, cache images, or disable schedules after 60 days of inactivity. Branch protection must permit the update bot to push if you enable it.

Conceptual reference: [Avi Vashishta's animated profile tutorial](https://www.avivashishta.com/blog/build-animated-github-profile-readme). The implementation keeps the self-contained SVG approach, but deliberately drops the dashboard composition.
