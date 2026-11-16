"""Builds index.html for aicontagionwatch.com from the JSON files in data/.

Usage: python3 build.py            (run from the repository root)
Only data/*.json changes between refreshes; this script turns it into a static page.
"""
import json, math, html, os, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(ROOT, 'data')
L = lambda n: json.load(open(os.path.join(D, n + '.json'), encoding='utf-8'))
ind, clock, trig, loop, notes = L('indicators'), L('clock'), L('triggers'), L('loop'), L('notes')
sinfo, scen, hist = L('scenario_info'), L('scenarios'), L('history')
meta = L('meta') if os.path.exists(os.path.join(D, 'meta.json')) else {}
note = {n['id']: n['text'] for n in notes}
e = lambda s: html.escape(str(s))

updated = meta.get('updated_label') or datetime.date.today().strftime('%-d %B %Y')
asof = meta.get('market_data_label', '')

GROUP_NAMES = {'Equities': 'Stock markets', 'Credit': 'Credit and financing',
               'Macro': 'Rates, inflation and oil', 'Havens': 'Metals'}
GROUP_NOTES = {'Equities': 'Where AI selling shows up first.',
               'Credit': 'Where a debt-funded bust usually breaks.',
               'Macro': 'The cost of money for everyone borrowing to build.',
               'Havens': 'What investors run to, and what industry needs.'}
STATUS_WORD = {'Stress': 'Stress', 'Watch': 'Watch', 'Calm': 'Calm'}

# ---- clock score
rows, total = [], 0.0
for r in clock:
    s = max(0.0, min(1.0, (r['now'] - r['calm']) / (r['breach'] - r['calm'])))
    total += s * r['weight']
    rows.append((r, s))
minutes = 10 * (1 - total)
level = 'stress' if total >= 0.66 else 'watch' if total >= 0.33 else 'calm'
level_word = {'stress': 'High fragility', 'watch': 'Elevated fragility', 'calm': 'Low fragility'}[level]


def clock_svg(minutes, S=320):
    c = S / 2; R = c - 10
    ang = lambda m: m / 60 * 2 * math.pi
    def arc(a0, a1, r0, r1):
        pt = lambda a, r: (c + math.sin(a) * r, c - math.cos(a) * r)
        large = 1 if a1 - a0 > math.pi else 0
        p1, p2, p3, p4 = pt(a0, r1), pt(a1, r1), pt(a1, r0), pt(a0, r0)
        return (f'M{p1[0]:.2f},{p1[1]:.2f} A{r1},{r1} 0 {large} 1 {p2[0]:.2f},{p2[1]:.2f} '
                f'L{p3[0]:.2f},{p3[1]:.2f} A{r0},{r0} 0 {large} 0 {p4[0]:.2f},{p4[1]:.2f} Z')
    o = [f'<svg class="clock-svg" viewBox="0 0 {S} {S}" role="img" '
         f'aria-label="Clock reading {minutes:.1f} minutes to midnight">',
         f'<circle cx="{c}" cy="{c}" r="{R}" class="c-face"/>',
         f'<path d="{arc(ang(50), ang(60), R-26, R-8)}" class="c-track"/>',
         f'<path d="{arc(ang(60 - minutes), ang(60), R-26, R-8)}" class="c-danger"/>']
    for m in range(60):
        a = ang(m); major = m % 5 == 0
        r0 = R - 34 if major else R - 31
        o.append(f'<line x1="{c+math.sin(a)*(R-38 if major else R-36):.2f}" y1="{c-math.cos(a)*(R-38 if major else R-36):.2f}" '
                 f'x2="{c+math.sin(a)*r0:.2f}" y2="{c-math.cos(a)*r0:.2f}" class="{"c-major" if major else "c-minor"}"/>')
    hour_deg = 360 - minutes * 0.5
    min_deg = (60 - minutes) * 6
    o.append(f'<g class="c-hour" style="transform:rotate({hour_deg:.2f}deg)"><line x1="{c}" y1="{c+14}" x2="{c}" y2="{c-R*0.48:.1f}"/></g>')
    o.append(f'<g class="c-min" style="--to:{min_deg:.2f}deg"><line x1="{c}" y1="{c+20}" x2="{c}" y2="{c-R+30:.1f}"/></g>')
    o.append(f'<circle cx="{c}" cy="{c}" r="7" class="c-hub"/></svg>')
    return ''.join(o)


def lvl(s):
    return 'stress' if s >= 0.66 else 'watch' if s >= 0.33 else 'calm'


drivers = ''.join(
    f'<li class="drv"><div class="drv-head"><span class="drv-name">{e(r["signal"])}</span>'
    f'<span class="drv-now">{e(r["now_display"])}</span></div>'
    f'<div class="drv-bar" role="img" aria-label="{e(r["signal"])}: {s:.0%} of the way from calm to breach">'
    f'<span class="drv-fill {lvl(s)}" style="width:{max(s,0.015)*100:.1f}%"></span></div>'
    f'<div class="drv-foot"><span>Calm</span><span>{e(r["thresholds"])} · weight {r["weight"]*100:g}%</span><span>Breach</span></div></li>'
    for r, s in sorted(rows, key=lambda x: -x[1] * x[0]['weight']))

# ---- gauges grouped
groups = []
for r in ind:
    if r['group'] not in [g for g, _ in groups]:
        groups.append((r['group'], []))
    next(lst for g, lst in groups if g == r['group']).append(r)

def gauge(r):
    st = r['status']
    return (f'<article class="g {st.lower()}"><header><h4>{e(r["label"])}</h4>'
            f'<span class="chip {st.lower()}">{e(STATUS_WORD.get(st, st))}</span></header>'
            f'<p class="g-val">{e(r["display"])}</p><p class="g-chg">{e(r["change"])}</p>'
            f'<p class="g-date">{e(r["asof"])}</p></article>')

gauges = ''.join(
    f'<div class="grp"><div class="grp-head"><h3>{e(GROUP_NAMES.get(g, g))}</h3>'
    f'<p>{e(GROUP_NOTES.get(g, ""))} '
    f'<span class="grp-count">{sum(1 for r in lst if r["status"]=="Stress")} of {len(lst)} under stress</span></p></div>'
    f'<div class="g-grid">{"".join(gauge(r) for r in lst)}</div></div>'
    for g, lst in groups)

stress_n = sum(1 for r in ind if r['status'] == 'Stress')

# ---- loop
loop_rows = ''.join(
    f'<li><div class="lp-flow">{e(r["flow"])}</div><div class="lp-amt">{e(r["amount"])}</div>'
    f'<div class="lp-type">{e(r["type"])}</div><div class="lp-note">{e(r["note"])}</div></li>' for r in loop)

# ---- warning signs
signs = ''.join(
    f'<li class="sg {t["state"].lower()}"><div class="sg-side"><span class="chip {t["state"].lower()}">{e(t["state"])}</span>'
    f'<span class="sg-status">{e(t["status"])}</span></div>'
    f'<div class="sg-main"><h3>{e(t["signal"])}</h3><p>{e(t["why"])}</p></div></li>' for t in trig)

# ---- scenarios
pct = lambda v: ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v)}%'

BUCKET_NAMES = {'Watchlist A — quality, AI-linked': 'Quality companies tied to AI demand'}

def scen_chart(sid):
    rs = [r for r in scen if r['scenario'] == sid]
    pos = lambda v: (v + 80) / 100 * 100
    ticks = ''.join(f'<span class="sx-tick" style="left:{pos(t):.1f}%">{pct(t)}</span>' for t in [-80, -60, -40, -20, 0, 20])
    grid = ''.join(f'<span class="sx-grid{" zero" if t == 0 else ""}" style="left:{pos(t):.1f}%"></span>' for t in [-80, -60, -40, -20, 0, 20])
    out = ''
    for r in rs:
        cls = 'ai' if r['bucket'].startswith('AI core') else 'gold' if r['bucket'].startswith('Gold') else 'base'
        name = BUCKET_NAMES.get(r['bucket'], r['bucket'])
        out += (f'<li><div class="sx-head"><span class="sx-name">{e(name)}</span>'
                f'<span class="sx-range">{pct(r["low"])} to {pct(r["high"])}</span></div>'
                f'<div class="sx-track">{grid}<span class="sx-bar {cls}" style="left:{pos(r["low"]):.1f}%;width:{max(1.0, pos(r["high"]) - pos(r["low"])):.1f}%"></span></div></li>')
    return (f'<div class="sx" role="img" aria-label="Illustrative fall ranges by group"><ul>{out}</ul>'
            f'<div class="sx-axis">{ticks}</div></div>')

scen_tabs = ''.join(
    f'<button type="button" role="tab" id="t-{si["id"]}" aria-controls="p-{si["id"]}" aria-selected="{"true" if i == 0 else "false"}">{e(si["name"])}</button>'
    for i, si in enumerate(sinfo))
scen_panels = ''.join(
    f'<div class="sc-panel" role="tabpanel" id="p-{si["id"]}" aria-labelledby="t-{si["id"]}"{"" if i == 0 else " hidden"}>'
    f'<p class="sc-desc">{e(si["description"])}</p><p class="sc-trig"><b>What would trigger it:</b> {e(si["trigger"])}</p>'
    f'{scen_chart(si["id"])}</div>' for i, si in enumerate(sinfo))
hist_rows = ''.join(
    f'<tr><td>{e(r["episode"])}</td><td>{e(r["asset"])}</td><td class="num">{e(r["drawdown"])}</td><td>{e(r["lesson"])}</td></tr>'
    for r in hist)

sources = ''.join(f'<li><b>{e(r["label"])}</b> ({e(r["asof"])}): {e(r["source"])}</li>' for r in ind)

title = 'AI Contagion Watch'
desc = ('How fragile is the money behind the AI boom? A minutes-to-midnight clock and live stress '
        'gauges tracking credit, capex, rates and the circular deals between chipmakers, AI labs and lenders.')

page = f'''<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}: {minutes:.1f} minutes to midnight</title>
<meta name="description" content="{e(desc)}">
<meta property="og:title" content="{title}: {minutes:.1f} minutes to midnight">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://aicontagionwatch.com/">
<meta name="theme-color" content="#0f2a3d">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='15' fill='%230f2a3d'/%3E%3Cpath d='M16 16 L5.2 9.8 A12.5 12.5 0 0 1 16 3.5 Z' fill='%23d8432f'/%3E%3Cpath d='M16 17V6M16 16l-7-4' stroke='%23fff' stroke-width='2.4' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">
<style>
:root {{
  --navy:#0f2a3d; --navy-2:#173a52; --fog:#eef1f3; --paper:#ffffff; --ink:#15212b; --slate:#56636e; --rule:#d3dae0;
  --signal:#d8432f; --stress:#c2362b; --watch:#b77b07; --calm:#2b7a6a; --steel:#3d6d93; --brass:#a9822f;
  --on-navy:#eaf0f4; --on-navy-dim:#9fb3c3;
  --sans:"Archivo", "Helvetica Neue", Arial, sans-serif; --serif:"Source Serif 4", Georgia, serif;
}}
@media (prefers-color-scheme: dark) {{ :root {{
  --fog:#0c1c28; --paper:#11273a; --ink:#e3eaef; --slate:#9fb0bd; --rule:#244055;
  --stress:#ef6a57; --watch:#e0a83a; --calm:#57b5a2; --steel:#7eaad0; --brass:#d2ad5c;
}} }}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; -webkit-text-size-adjust:100%; }}
body {{ margin:0; background:var(--fog); color:var(--ink); font:400 16px/1.5 var(--sans); font-variation-settings:"wdth" 100; }}
a {{ color:inherit; }}
:focus-visible {{ outline:3px solid var(--signal); outline-offset:2px; }}
.w {{ max-width:1160px; margin:0 auto; padding:0 20px; }}
.num, .g-val, .lp-amt, .drv-now, .big {{ font-variant-numeric:tabular-nums; }}

/* masthead + hero */
.mast {{ background:var(--navy); color:var(--on-navy); }}
.bar {{ display:flex; align-items:center; gap:24px; height:56px; border-bottom:1px solid rgba(255,255,255,.12); }}
.logo {{ display:flex; align-items:center; gap:10px; text-decoration:none; font-weight:700; font-variation-settings:"wdth" 112; letter-spacing:-.01em; font-size:17px; white-space:nowrap; }}
.logo svg {{ width:24px; height:24px; }}
.nav {{ display:flex; gap:22px; margin-left:auto; overflow-x:auto; scrollbar-width:none; }}
.nav a {{ color:var(--on-navy-dim); text-decoration:none; font-size:14px; white-space:nowrap; padding:6px 0; }}
.nav a:hover {{ color:#fff; }}
.hero {{ display:grid; grid-template-columns:minmax(260px,360px) 1fr; gap:48px; align-items:center; padding:48px 0 40px; }}
.clock-svg {{ width:100%; height:auto; display:block; }}
.c-face {{ fill:var(--navy-2); stroke:rgba(255,255,255,.18); stroke-width:1.5; }}
.c-track {{ fill:rgba(255,255,255,.10); }} .c-danger {{ fill:var(--signal); }}
.c-major {{ stroke:#fff; stroke-width:3; stroke-linecap:round; }} .c-minor {{ stroke:rgba(255,255,255,.35); stroke-width:1.2; }}
.c-hour line {{ stroke:#fff; stroke-width:8; stroke-linecap:round; }}
.c-min line {{ stroke:#fff; stroke-width:4; stroke-linecap:round; }}
.c-hour, .c-min {{ transform-origin:50% 50%; transform-box:view-box; }}
.c-min {{ transform:rotate(var(--to)); }}
.c-hub {{ fill:var(--signal); stroke:var(--navy); stroke-width:3; }}
@media (prefers-reduced-motion: no-preference) {{
  .c-min {{ animation:sweep 1.6s cubic-bezier(.2,.8,.2,1) .2s both; }}
  @keyframes sweep {{ from {{ transform:rotate(300deg); }} to {{ transform:rotate(var(--to)); }} }}
}}
.reading {{ display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; }}
.big {{ font-size:clamp(84px,14vw,168px); line-height:.85; font-weight:800; font-variation-settings:"wdth" 125; letter-spacing:-.03em; color:#fff; }}
.big-unit {{ font-size:clamp(20px,2.6vw,28px); font-weight:500; font-variation-settings:"wdth" 88; color:var(--on-navy); line-height:1.15; max-width:9ch; }}
.level {{ display:inline-flex; align-items:center; gap:8px; margin:18px 0 0; padding:5px 12px 5px 10px; border-radius:999px; background:rgba(216,67,47,.16); color:#ffb4a8; font-weight:600; font-size:14px; }}
.level::before {{ content:""; width:8px; height:8px; border-radius:50%; background:var(--signal); }}
.level.calm {{ background:rgba(87,181,162,.16); color:#9fe0d1; }} .level.calm::before {{ background:#57b5a2; }}
.takeaway {{ font-family:var(--serif); font-size:clamp(18px,1.8vw,21px); line-height:1.55; color:var(--on-navy); max-width:38em; margin:20px 0 0; }}
.stamp {{ color:var(--on-navy-dim); font-size:13.5px; margin:16px 0 0; }}

/* drivers */
.drivers {{ background:var(--navy-2); border-radius:6px; padding:24px 24px 8px; }}
.mast {{ padding-bottom:48px; }}
.drivers h2 {{ color:#fff; }} .drivers > p {{ color:var(--on-navy-dim); }}
.drv-list {{ list-style:none; margin:20px 0 0; padding:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr)); gap:4px 36px; }}
.drv {{ padding:12px 0 14px; border-top:1px solid rgba(255,255,255,.12); color:var(--on-navy); }}
.drv-head {{ display:flex; justify-content:space-between; gap:12px; align-items:baseline; }}
.drv-name {{ font-weight:600; font-size:15px; }}
.drv-now {{ font-size:13.5px; color:var(--on-navy-dim); text-align:right; max-width:58%; }}
.drv-bar {{ height:10px; background:rgba(255,255,255,.10); border-radius:2px; margin:10px 0 6px; overflow:hidden; }}
.drv-fill {{ display:block; height:100%; border-radius:2px; }}
.drv-fill.calm {{ background:#57b5a2; }} .drv-fill.watch {{ background:#e0a83a; }} .drv-fill.stress {{ background:var(--signal); }}
.drv-foot {{ display:flex; justify-content:space-between; gap:8px; font-size:12px; color:var(--on-navy-dim); }}
.drv-foot span:nth-child(2) {{ text-align:center; }}

/* body sections */
main {{ padding-top:8px; }}
section {{ padding:56px 0 8px; scroll-margin-top:16px; }}
h2 {{ font-size:clamp(24px,3vw,32px); line-height:1.15; font-weight:700; font-variation-settings:"wdth" 108; letter-spacing:-.015em; margin:0 0 8px; }}
.intro {{ font-family:var(--serif); font-size:17.5px; line-height:1.6; color:var(--slate); max-width:40em; margin:0 0 28px; }}
h3 {{ font-size:18px; font-weight:650; margin:0; letter-spacing:-.005em; }}

.chip {{ display:inline-flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; padding:2px 9px 2px 7px; border-radius:999px; white-space:nowrap; }}
.chip::before {{ content:""; width:7px; height:7px; border-radius:50%; background:currentColor; }}
.chip.stress {{ color:var(--stress); background:color-mix(in srgb, var(--stress) 12%, transparent); }}
.chip.watch {{ color:var(--watch); background:color-mix(in srgb, var(--watch) 14%, transparent); }}
.chip.calm {{ color:var(--calm); background:color-mix(in srgb, var(--calm) 13%, transparent); }}

.grp {{ display:grid; grid-template-columns:220px 1fr; gap:32px; padding:28px 0; border-top:2px solid var(--ink); }}
.grp-head p {{ color:var(--slate); font-size:14.5px; margin:8px 0 0; }}
.grp-count {{ display:block; margin-top:10px; font-weight:600; color:var(--ink); }}
.g-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,250px),1fr)); gap:12px; }}
.g {{ background:var(--paper); padding:16px 16px 14px; display:flex; flex-direction:column; gap:6px; border:1px solid var(--rule); border-top:3px solid var(--rule); border-radius:0 0 4px 4px; }}
.g.stress {{ border-top-color:var(--stress); }} .g.watch {{ border-top-color:var(--watch); }} .g.calm {{ border-top-color:var(--calm); }}
.g header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:10px; }}
.g h4 {{ margin:0; font-size:14px; font-weight:600; color:var(--slate); line-height:1.3; }}
.g-val {{ margin:2px 0 0; font-size:30px; line-height:1.05; font-weight:700; font-variation-settings:"wdth" 118; letter-spacing:-.02em; }}
.g-chg {{ margin:0; font-size:14px; line-height:1.5; }}
.g-date {{ margin:auto 0 0; padding-top:6px; font-size:12.5px; color:var(--slate); }}

.loop-wrap {{ display:grid; grid-template-columns:minmax(0,1fr) minmax(0,2fr); gap:40px; align-items:start; }}
.imf {{ font-family:var(--serif); font-size:18px; line-height:1.6; border-left:4px solid var(--signal); padding:4px 0 4px 20px; margin:0; }}
.imf-src {{ font-family:var(--sans); display:block; font-size:13px; color:var(--slate); margin-top:10px; }}
.lp {{ list-style:none; margin:0; padding:0; border-top:2px solid var(--ink); }}
.lp li {{ display:grid; grid-template-columns:1fr auto; gap:2px 20px; padding:14px 0; border-bottom:1px solid var(--rule); }}
.lp-flow {{ font-weight:650; }}
.lp-amt {{ font-weight:700; font-variation-settings:"wdth" 115; text-align:right; white-space:nowrap; }}
.lp-type {{ font-size:13px; color:var(--slate); grid-column:2; grid-row:2; text-align:right; }}
.lp-note {{ font-size:14.5px; color:var(--slate); grid-column:1; grid-row:2; }}

.sg-list {{ list-style:none; margin:0; padding:0; border-top:2px solid var(--ink); }}
.sg {{ display:grid; grid-template-columns:200px 1fr; gap:28px; padding:20px 0; border-bottom:1px solid var(--rule); }}
.sg-side {{ display:flex; flex-direction:column; align-items:flex-start; gap:8px; }}
.sg-status {{ font-weight:650; font-size:15px; line-height:1.3; }}
.sg-main p {{ font-family:var(--serif); font-size:16.5px; line-height:1.6; margin:6px 0 0; max-width:44em; }}

.sc {{ background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:24px; }}
.tabs {{ display:inline-flex; flex-wrap:wrap; gap:4px; padding:4px; background:var(--fog); border-radius:8px; margin-bottom:20px; }}
.tabs button {{ font:inherit; font-size:14.5px; font-weight:600; border:0; background:none; color:var(--slate); padding:8px 14px; border-radius:6px; cursor:pointer; }}
.tabs button[aria-selected="true"] {{ background:var(--navy); color:#fff; }}
.sc-desc {{ font-family:var(--serif); font-size:17px; line-height:1.6; max-width:44em; margin:0 0 8px; }}
.sc-trig {{ font-size:14.5px; color:var(--slate); max-width:56em; margin:0 0 20px; }}
.sx ul {{ list-style:none; margin:0; padding:0; }}
.sx li {{ padding:10px 0; }}
.sx-head {{ display:flex; justify-content:space-between; gap:12px; font-size:15px; margin-bottom:6px; }}
.sx-name {{ font-weight:600; }} .sx-range {{ color:var(--slate); white-space:nowrap; font-variant-numeric:tabular-nums; }}
.sx-track {{ position:relative; height:16px; }}
.sx-grid {{ position:absolute; top:-4px; bottom:-4px; width:1px; background:var(--rule); }}
.sx-grid.zero {{ background:none; border-left:1px dashed var(--slate); }}
.sx-bar {{ position:absolute; top:2px; height:12px; border-radius:2px; background:var(--steel); }}
.sx-bar.ai {{ background:var(--stress); }} .sx-bar.gold {{ background:var(--brass); }}
.sx-axis {{ position:relative; height:22px; margin-top:6px; font-size:12px; color:var(--slate); }}
.sx-tick {{ position:absolute; transform:translateX(-50%); white-space:nowrap; font-variant-numeric:tabular-nums; }}
.sx-tick:first-child {{ transform:none; }} .sx-tick:last-child {{ transform:translateX(-100%); }}
.s-grid {{ stroke:var(--rule); }} .s-zero {{ stroke:var(--slate); stroke-dasharray:3 3; }}
.s-tick {{ fill:var(--slate); font:12px var(--sans); }} .s-name {{ fill:var(--ink); font:600 14px var(--sans); }}
.s-bar {{ fill:var(--steel); }} .s-ai {{ fill:var(--stress); }} .s-gold {{ fill:var(--brass); }}
.hist {{ margin-top:28px; }}
.tw {{ overflow-x:auto; }}
table {{ width:100%; min-width:600px; border-collapse:collapse; font-size:14.5px; }}
th {{ text-align:left; font-weight:600; color:var(--slate); padding:8px 12px 8px 0; border-bottom:2px solid var(--ink); }}
td {{ padding:10px 12px 10px 0; border-bottom:1px solid var(--rule); vertical-align:top; }}
td.num {{ white-space:nowrap; font-weight:650; }}

.about {{ display:grid; grid-template-columns:1fr 1fr; gap:40px; }}
.notice {{ background:var(--paper); border:1px solid var(--rule); border-left:4px solid var(--watch); padding:20px 22px; border-radius:4px; }}
.about p {{ font-family:var(--serif); font-size:16.5px; line-height:1.6; margin:0 0 12px; }}
.about h3 {{ margin-bottom:10px; }}

footer {{ background:var(--navy); color:var(--on-navy-dim); margin-top:72px; padding:40px 0 48px; font-size:13.5px; line-height:1.55; }}
footer h3 {{ color:#fff; font-size:15px; margin-bottom:12px; }}
footer ul {{ margin:0; padding-left:18px; columns:2 420px; column-gap:40px; }}
footer li {{ margin:0 0 6px; break-inside:avoid; }}
footer .fine {{ margin:28px 0 0; padding-top:20px; border-top:1px solid rgba(255,255,255,.12); }}

@media (max-width: 860px) {{
  .hero {{ grid-template-columns:1fr; gap:28px; padding-top:32px; }}
  .clock-box {{ max-width:260px; }}
  .grp, .sg, .loop-wrap, .about {{ grid-template-columns:1fr; gap:16px; }}
  .drivers {{ padding:20px 16px 4px; }}
}}
@media (max-width: 520px) {{
  .bar {{ gap:14px; }} .nav {{ gap:16px; }}
  .drv-foot span:nth-child(2) {{ display:none; }}
  .sc {{ padding:16px; }}
}}
</style>
</head>
<body>
<div class="mast">
<div class="w">
<div class="bar">
<a class="logo" href="#top"><svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="14.5" fill="none" stroke="#fff" stroke-opacity=".5" stroke-width="1.5"/><path d="M16 16 L5.2 9.8 A12.5 12.5 0 0 1 16 3.5 Z" fill="#d8432f"/><path d="M16 17V6M16 16l-7-4" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg>AI Contagion Watch</a>
<nav class="nav" aria-label="Sections"><a href="#gauges">Gauges</a><a href="#loop">The loop</a><a href="#signs">Warning signs</a><a href="#scenarios">Scenarios</a><a href="#about">About</a></nav>
</div>
<div class="hero" id="top">
<div class="clock-box">{clock_svg(minutes)}</div>
<div>
<div class="reading"><span class="big">{minutes:.1f}</span><span class="big-unit">minutes to midnight</span></div>
<span class="level {level}">{level_word}: score {total:.2f} out of 1</span>
<p class="takeaway">{e(note["takeaway"])}</p>
<p class="stamp">Updated {e(updated)}{(", " + e(asof)) if asof else ""}.</p>
</div>
</div>
<div class="drivers" aria-labelledby="drivers-h">
<h2 id="drivers-h">What’s moving the clock</h2>
<p>Each bar shows how far a signal has travelled from its calm level to its breach level. Bigger contributors are listed first. Weights and thresholds are a judgement call, not an established index.</p>
<ul class="drv-list">{drivers}</ul>
</div>
</div>
</div>

<main class="w">
<section id="gauges">
<h2>Where the stress is showing</h2>
<p class="intro">{stress_n} of {len(ind)} gauges are flashing stress. Each reading carries its own date, because some figures, such as credit default swap prices, are published irregularly.</p>
{gauges}
</section>

<section id="loop">
<h2>The loop, traced</h2>
<p class="intro">Much of the AI build-out is paid for by the same handful of companies investing in, lending to and buying from each other. If one link fails, the others feel it.</p>
<div class="loop-wrap">
<blockquote class="imf">{e(note["imf"])}<span class="imf-src">International Monetary Fund, Global Financial Stability Report, October 2026</span></blockquote>
<ul class="lp">{loop_rows}</ul>
</div>
</section>

<section id="signs">
<h2>Warning signs to watch</h2>
<p class="intro">The developments most likely to move the clock in the weeks ahead.</p>
<ul class="sg-list">{signs}</ul>
</section>

<section id="scenarios">
<h2>If it breaks: how far things could fall</h2>
<p class="intro">Three illustrative scenarios, anchored to past busts. These are assumptions, not forecasts. In a forced-selling phase almost everything falls together, gold miners included; what differs is how well margins hold and how fast prices recover.</p>
<div class="sc">
<div class="tabs" role="tablist" aria-label="Scenarios">{scen_tabs}</div>
{scen_panels}
<div class="hist"><h3>What past busts did</h3>
<div class="tw"><table><thead><tr><th>Episode</th><th>Asset</th><th>Fall</th><th>Lesson</th></tr></thead><tbody>{hist_rows}</tbody></table></div>
<p class="sc-trig" style="margin-top:10px">Approximate peak-to-trough falls, rounded from market history.</p></div>
</div>
</section>

<section id="about">
<h2>About this page</h2>
<div class="about">
<div class="notice"><h3>General information only</h3>
<p>This site is general market commentary for information and education. It is not financial product advice and does not take into account your objectives, financial situation or needs. It does not recommend buying, selling or holding any financial product. Consider getting advice from a licensed financial adviser before making any investment decision. Past performance is not a reliable indicator of future performance.</p></div>
<div><h3>How it’s made</h3>
<p>Figures are compiled from public reporting, with the source for each listed below, and refreshed periodically, so they lag live markets. Statuses, the clock’s weights and thresholds, and the scenarios are judgements.</p>
<p>Claude, an AI model, is used to research and generate this dashboard’s data. Claude is owned by Anthropic, one of the key players in the AI financing boom whose risk of economic contagion this site tracks.</p></div>
</div>
</section>
</main>

<footer><div class="w">
<h3>Sources for the gauges</h3>
<ul>{sources}</ul>
<p class="fine">© {datetime.date.today().year} AI Contagion Watch. General information only, not financial advice.</p>
</div></footer>
<script>
document.querySelectorAll('[role="tablist"]').forEach(function (list) {{
  var tabs = list.querySelectorAll('[role="tab"]');
  tabs.forEach(function (tab, i) {{
    tab.addEventListener('click', function () {{
      tabs.forEach(function (t) {{
        var on = t === tab; t.setAttribute('aria-selected', on);
        document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
      }});
    }});
    tab.addEventListener('keydown', function (ev) {{
      var d = ev.key === 'ArrowRight' ? 1 : ev.key === 'ArrowLeft' ? -1 : 0;
      if (d) {{ var n = tabs[(i + d + tabs.length) % tabs.length]; n.focus(); n.click(); }}
    }});
  }});
}});
</script>
</body>
</html>
'''
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(page)
print(f'index.html written: {minutes:.1f} minutes to midnight (score {total:.3f})')
