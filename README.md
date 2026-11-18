# AI Contagion Watch

Static site for https://aicontagionwatch.com, served by GitHub Pages.

- `data/*.json` holds the figures (the same data as the private AI Contagion Watch dashboard, without the watchlists).
- `build.py` turns the data into `index.html`, then calls `gauges.py`, which builds the Australian gauges page at `oz-gauges/index.html` and its shareable image `oz-gauges/oz-gauges.png` (needs Playwright). Run `python3 build.py` after changing anything in `data/`.
- `data/gauges.json` holds the inputs for the temperature and pressure dials; the speed dial is calculated from the clock and `australia.json`. `data/clock_trail.json` keeps one clock reading per day (the build adds today's) for the speed trend.
- `CNAME` points GitHub Pages at the custom domain.

## Refreshing

1. Update the files in `data/` (`indicators`, `clock`, `triggers`, `loop`, `notes`, `australia`, `gauges`; set the labels in `meta.json`).
2. Run `python3 build.py`.
3. Commit `data/`, `index.html` and `oz-gauges/` and push to `main`. Pages republishes within a minute or two.

General information only, not financial product advice.
