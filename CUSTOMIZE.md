# Keeping this workspace yours

Requires Python 3.11+; Actions uses 3.13. No packages to install, so no requirements file.

```sh
python -m scripts.generate            # deterministic, offline: committed snapshot
python -m scripts.generate --refresh  # fetch public data, then regenerate all assets
python -m unittest discover -s tests -v
```

## Change the design

- **Text:** edit `tagline` in `profile.json`; edit projects and links in `README.md`.
- **Statistics / displayed data:** `scripts/artwork.py`, especially `terminal()` and `contributions()`. The snapshot is generated, not hand-maintained.
- **Technologies:** `profile.json` holds curated labels with verified source URLs. They describe repository code, not proficiency. Add evidence with each new label. Labels are shown only while their project remains public and original.
- **Dimensions:** `width` scales the SVGs proportionally; adjust README image widths too. Internal layout uses an 840-unit `viewBox`; change coordinates/heights in `artwork.py` for a different composition.
- **Speed:** `motion_seconds` controls fades and the pipeline trace. The short cursor sequence is defined separately in `svg()`. Animations stop, and reduced-motion preferences disable them entirely.
- **Style:** edit the hex palette in `profile.json`, or the system-font stack in `svg()`. No font downloads, scripts, or external image resources.
- **Portrait later:** replace `visual()` with a renderer for ASCII rows derived from a photo you choose to provide. Keep the accessible title/description, static final state, and local SVG output. The current pipeline is deliberately abstract, not a likeness.

## Data and scope

Public REST endpoints supply owned repositories and followers. Languages are the three most frequent **primary languages per original public project**, alphabetically breaking ties—not a claim about skill or a byte-weighted ranking. Forks and this profile repository are excluded from languages and star totals; the public repository count includes both.

The contribution source is GitHub's **anonymous public calendar HTML**, fetched without credentials. Exact tooltip counts and intensity levels are stored with dates in `data/profile.json`. GitHub may include anonymized private activity if you enable that on your profile; this is a publicly visible calendar, **not a guaranteed public-repositories-only count**. No private repository names or details are fetched. The SVG labels the actual date range (GitHub may include a partial boundary week). Today can be incomplete.

The parser validates counts, levels, continuous dates, and calendar freshness. If GitHub changes its HTML or requests fail, generation fails rather than publishing invented zeros; the last committed assets remain available. `as_of` is a UTC retrieval date, not a live status indicator. The dated snapshot is intentional for reproducibility and offline testing.

Project descriptions and technology evidence were reviewed against the public Bindery and SomnoRoute READMEs and SWODS package manifest. No professional title, employer, education, years of experience, email, or social handle is asserted. The tagline is editable neutral copy. No personal placeholders appear on the profile; add verified links in README when you want them.

## Updates

`.github/workflows/update-profile.yml` runs at **06:23 UTC daily**, manually from Actions, and on generator/config changes to `main`. It tests, refreshes, validates, and commits only changed SVGs and snapshot data. Actions are pinned to commit SHAs; there are no pip dependencies. Only the update job receives `contents: write`. The built-in `GITHUB_TOKEN` is sufficient; no custom secrets or personal access token are required.

Failures appear in Actions; inspect the failed run and rerun after fixing the source/parser. Scheduled jobs can be delayed, and GitHub can disable schedules in public repos after 60 days of inactivity; re-enable the workflow if necessary. Branch protection that forbids bot pushes needs a compatible repository policy. Concurrent runs are serialized and a conflicting push fails safely rather than force-pushing.

SVGs are embedded as ordinary README images with alt text. Their background and foreground colors are self-contained for both GitHub themes; content remains visible if CSS animation is unavailable. Fine calendar details are naturally smaller on phones. GitHub image caching can delay visible refreshes.

Conceptual reference: [Avi Vashishta's animated profile tutorial](https://www.avivashishta.com/blog/build-animated-github-profile-readme). This implementation uses its local-SVG/public-calendar approach, but original artwork, shared standard-library renderers, no portrait pipeline, and no third-party stats service.
