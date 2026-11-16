# AI Contagion Watch

Static site for https://aicontagionwatch.com, served by GitHub Pages.

- `data/*.json` holds the figures (the same data as the private AI Contagion Watch dashboard, without the watchlists).
- `build.py` turns the data into `index.html`. Run `python3 build.py` after changing anything in `data/`.
- `CNAME` points GitHub Pages at the custom domain.

## Refreshing

1. Update the files in `data/` (`indicators`, `clock`, `triggers`, `loop`, `notes`; set the labels in `meta.json`).
2. Run `python3 build.py`.
3. Commit `data/` and `index.html` and push to `main`. Pages republishes within a minute or two.

General information only, not financial product advice.
