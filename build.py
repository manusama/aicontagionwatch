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

# ---- clock
rows, total = [], 0.0
for r in clock:
    s = max(0.0, min(1.0, (r['now'] - r['calm']) / (r['breach'] - r['calm'])))
    total += s * r['weight']
    rows.append((r, s))
minutes = 10 * (1 - total)


def dial(minutes, S=220):
    c = S / 2; R = c - 18
    ang = lambda m: m / 60 * 2 * math.pi
    def arc(a0, a1, r0, r1):
        pt = lambda a, r: (c + math.sin(a) * r, c - math.cos(a) * r)
        large = 1 if a1 - a0 > math.pi else 0
        p1, p2, p3, p4 = pt(a0, r1), pt(a1, r1), pt(a1, r0), pt(a0, r0)
        return (f'M{p1[0]:.2f},{p1[1]:.2f} A{r1},{r1} 0 {large} 1 {p2[0]:.2f},{p2[1]:.2f} '
                f'L{p3[0]:.2f},{p3[1]:.2f} A{r0},{r0} 0 {large} 0 {p4[0]:.2f},{p4[1]:.2f} Z')
    o = [f'<svg class="dial" viewBox="0 0 {S} {S}" role="img" aria-label="Clock showing {minutes:.1f} minutes to midnight">',
         f'<circle cx="{c}" cy="{c}" r="{R}" class="face"/>',
         f'<path d="{arc(ang(50), ang(60), R-14, R-2)}" class="track"/>',
         f'<path d="{arc(ang(50), ang(60 - minutes), R-14, R-2)}" class="danger"/>']
    for m in range(0, 60, 5):
        a = ang(m)
        o.append(f'<line x1="{c+math.sin(a)*(R-20):.2f}" y1="{c-math.cos(a)*(R-20):.2f}" '
                 f'x2="{c+math.sin(a)*(R-28):.2f}" y2="{c-math.cos(a)*(R-28):.2f}" class="tick" '
                 f'stroke-width="{2.5 if m == 0 else 1.4}"/>')
    a = ang(60 - minutes)
    o.append(f'<line x1="{c}" y1="{c}" x2="{c+math.sin(a)*(R-18):.2f}" y2="{c-math.cos(a)*(R-18):.2f}" class="hand" stroke-width="3"/>')
    o.append(f'<line x1="{c}" y1="{c}" x2="{c}" y2="{c-R*0.5:.2f}" class="hand" stroke-width="5"/>')
    o.append(f'<circle cx="{c}" cy="{c}" r="5" class="hub"/>')
    o.append(f'<text x="{c}" y="11" text-anchor="middle" class="lbl">Midnight</text></svg>')
    return ''.join(o)


pct = lambda v: ('+' if v > 0 else '−' if v < 0 else '') + f'{abs(v)}%'


def scen_chart(sid, W=760):
    rs = [r for r in scen if r['scenario'] == sid]
    rowH, top, bot = 46, 4, 22
    H = top + len(rs) * rowH + bot
    x = lambda v: 4 + (v + 80) / 100 * (W - 8)
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Illustrative drawdown ranges">']
    for t in [-80, -60, -40, -20, 0, 20]:
        cls = 'zero' if t == 0 else 'grid'
        anchor = 'start' if t == -80 else 'end' if t == 20 else 'middle'
        o.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top}" y2="{H-bot}" class="{cls}"/>')
        o.append(f'<text x="{x(t):.1f}" y="{H-6}" text-anchor="{anchor}" class="lbl">{pct(t)}</text>')
    for i, r in enumerate(rs):
        y = top + i * rowH
        cls = 'bar-ai' if r['bucket'].startswith('AI core') else 'bar-gold' if r['bucket'].startswith('Gold') else 'bar'
        o.append(f'<text x="4" y="{y+14}" class="name">{e(r["bucket"])}</text>')
        o.append(f'<text x="{W-4}" y="{y+14}" text-anchor="end" class="lbl">{pct(r["low"])} to {pct(r["high"])}</text>')
        o.append(f'<rect x="{x(r["low"]):.1f}" y="{y+21}" width="{max(4, x(r["high"])-x(r["low"])):.1f}" height="14" rx="4" class="{cls}"/>')
    o.append('</svg>')
    return ''.join(o)


def table(cols, data):
    h = ''.join(f'<th>{e(c[1])}</th>' for c in cols)
    b = ''
    for r in data:
        cells = ''
        for k, _ in cols:
            v = r.get(k, '')
            if k == 'status' and 'state' in r:
                cells += f'<td class="c-{k}"><span class="dot {e(r["state"])}"></span>{e(v)}</td>'
            else:
                cells += f'<td class="c-{k}">{e(v)}</td>'
        b += f'<tr>{cells}</tr>'
    return f'<div class="tw"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


tiles = ''.join(
    f'<div class="tile"><div class="tt"><span class="tl">{e(r["label"])}</span>'
    f'<span class="pill"><span class="dot {e(r["status"])}"></span>{e(r["status"])}</span></div>'
    f'<div class="tv">{e(r["display"])}</div><div class="tc">{e(r["change"])}</div>'
    f'<div class="ta">{e(r["asof"])}</div></div>' for r in ind)

clock_rows = ''.join(
    f'<tr><td class="c-signal">{e(r["signal"])}</td><td>{e(r["thresholds"])}</td>'
    f'<td class="num">{e(r["now_display"])}</td><td class="num">{r["weight"]*100:g}%</td>'
    f'<td class="num">{s:.2f}<span class="bar-s"><span style="width:{s*100:.0f}%"></span></span></td></tr>'
    for r, s in rows)

scen_blocks = ''.join(
    f'<div class="card"><h3>{e(si["name"])}</h3><p>{e(si["description"])}</p>'
    f'<p class="muted small">Trigger: {e(si["trigger"])}</p>{scen_chart(si["id"])}</div>' for si in sinfo)

sources = ''.join(f'<li><b>{e(r["label"])}</b> ({e(r["asof"])}): {e(r["source"])}</li>' for r in ind)

title = 'AI Contagion Watch'
desc = ('Tracking the stress in the circular financing behind the AI boom: credit, capex, rates and a '
        'minutes-to-midnight fragility clock.')

page = f'''<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{e(desc)}">
<meta property="og:title" content="{title}: {minutes:.1f} minutes to midnight">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://aicontagionwatch.com/">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='14' fill='%23fff' stroke='%23b5402e' stroke-width='3'/%3E%3Cpath d='M16 16V5M16 16l-5-3' stroke='%231f1e1c' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Lora:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{ --bg:#fbfaf7; --panel:#f3f0e9; --fg:#1f1e1c; --muted:#6b675f; --line:#dedad2; --grid:#e7e3db;
  --bad:#b5402e; --warn:#a8720e; --ok:#3f7a4a; --blue:#3b5f8a; --gold:#b8892b; --face:#fff; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#161614; --panel:#201f1c; --fg:#ece9e2; --muted:#a39e94; --line:#38362f;
  --grid:#2e2c27; --bad:#e0705c; --warn:#d9a441; --ok:#7bb886; --blue:#7fa3cf; --gold:#d9ad55; --face:#1b1a18; }} }}
* {{ box-sizing:border-box; }}
html {{ scroll-behavior:smooth; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.55 Inter, system-ui, sans-serif; }}
.wrap {{ max-width:1080px; margin:0 auto; padding:0 16px; }}
header.top {{ border-bottom:1px solid var(--line); position:sticky; top:0; background:var(--bg); z-index:5; }}
header.top .wrap {{ display:flex; align-items:center; gap:16px; height:52px; overflow-x:auto; }}
.brand {{ font-family:Lora, serif; font-size:18px; white-space:nowrap; text-decoration:none; color:var(--fg); }}
nav a {{ color:var(--muted); text-decoration:none; font-size:14px; margin-left:14px; white-space:nowrap; }}
nav a:hover {{ color:var(--fg); }}
nav {{ display:flex; margin-left:auto; }}
.hero {{ padding:40px 0 8px; }}
.kicker {{ font-size:13px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }}
h1 {{ font-family:Lora, serif; font-weight:400; font-size:clamp(32px,6vw,52px); line-height:1.1; margin:8px 0 14px; }}
.lede {{ font-size:18px; max-width:62rem; margin:0; }}
section {{ padding:28px 0 8px; scroll-margin-top:60px; }}
h2 {{ font-size:22px; font-weight:600; margin:0 0 6px; }}
h3 {{ font-size:16px; font-weight:600; margin:0 0 6px; }}
p {{ margin:0 0 10px; }}
.muted {{ color:var(--muted); }} .small {{ font-size:14px; }}
.sub {{ color:var(--muted); font-size:14px; margin:0 0 16px; max-width:62rem; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:20px; margin-bottom:16px; }}
.clock {{ display:flex; flex-wrap:wrap; gap:28px; align-items:center; }}
.dial {{ width:min(100%,220px); height:auto; flex:none; }}
.dial .face {{ fill:var(--face); stroke:var(--line); stroke-width:1.5; }} .dial .track {{ fill:var(--grid); }}
.dial .danger {{ fill:var(--bad); }} .dial .tick {{ stroke:var(--muted); stroke-linecap:round; }}
.dial .hand {{ stroke:var(--fg); stroke-linecap:round; }} .dial .hub {{ fill:var(--fg); }}
svg .lbl {{ fill:var(--muted); font-size:11px; font-family:Inter, sans-serif; }}
svg .name {{ fill:var(--fg); font-size:13px; font-family:Inter, sans-serif; }}
svg .grid {{ stroke:var(--grid); }} svg .zero {{ stroke:var(--muted); stroke-dasharray:4 3; }}
svg .bar {{ fill:var(--blue); }} svg .bar-ai {{ fill:var(--bad); }} svg .bar-gold {{ fill:var(--gold); }}
.cnum {{ font-family:Lora, serif; font-size:clamp(48px,9vw,72px); line-height:1; }}
.cnum small {{ font-family:Inter; font-size:16px; color:var(--muted); margin-left:8px; }}
.ctext {{ flex:1 1 300px; }}
.tiles {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(min(100%,240px),1fr)); gap:12px; }}
.tile {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; display:flex; flex-direction:column; gap:6px; }}
.tt {{ display:flex; justify-content:space-between; gap:8px; align-items:baseline; }}
.tl {{ font-size:13px; color:var(--muted); }} .pill {{ font-size:12px; white-space:nowrap; }}
.tv {{ font-family:Lora, serif; font-size:26px; line-height:1.15; font-variant-numeric:tabular-nums; }}
.tc {{ font-size:13.5px; line-height:1.45; }} .ta {{ font-size:12px; color:var(--muted); margin-top:auto; }}
.dot {{ display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; vertical-align:1px; }}
.dot.Stress {{ background:var(--bad); }} .dot.Watch {{ background:var(--warn); }} .dot.Calm {{ background:var(--ok); }}
.tw {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
th {{ text-align:left; font-weight:500; color:var(--muted); border-bottom:1px solid var(--line); padding:6px 10px; vertical-align:bottom; }}
td {{ border-bottom:1px solid var(--line); padding:9px 10px; vertical-align:top; }}
tr:last-child td {{ border-bottom:0; }}
td.c-signal, td.c-flow, td.c-episode {{ font-weight:600; min-width:9rem; }}
td.c-status, td.c-amount, td.c-drawdown, .num {{ white-space:nowrap; font-variant-numeric:tabular-nums; }}
.bar-s {{ display:inline-block; width:48px; height:6px; background:var(--grid); border-radius:6px; margin-left:8px; vertical-align:middle; overflow:hidden; }}
.bar-s span {{ display:block; height:100%; background:var(--bad); }}
.grid2 {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr)); gap:16px; }}
.warn {{ border-left:3px solid var(--warn); }}
footer {{ border-top:1px solid var(--line); margin-top:32px; padding:24px 0 40px; color:var(--muted); font-size:13.5px; }}
footer ul {{ padding-left:18px; }} footer li {{ margin-bottom:4px; }}
a {{ color:inherit; }}
</style>
</head>
<body>
<header class="top"><div class="wrap">
<a class="brand" href="#">AI Contagion Watch</a>
<nav><a href="#clock">Clock</a><a href="#gauges">Gauges</a><a href="#loop">The loop</a><a href="#signals">Warning signs</a><a href="#scenarios">Scenarios</a><a href="#about">About</a></nav>
</div></header>
<main class="wrap">
<div class="hero">
<div class="kicker">Updated {e(updated)}{(' · ' + e(asof)) if asof else ''}</div>
<h1>How close is the AI boom to breaking?</h1>
<p class="lede">{e(note["takeaway"])}</p>
</div>

<section id="clock">
<h2>Minutes to midnight</h2>
<p class="sub">A composite fragility score. Each signal scores 0 at its calm level and 1 at its breach level; the weighted total maps to the last ten minutes before midnight. It measures how fragile things are, not when they will break.</p>
<div class="card"><div class="clock">{dial(minutes)}<div class="ctext">
<div class="cnum">{minutes:.1f}<small>minutes to midnight</small></div>
<p>Composite fragility score <b>{total:.2f}</b> out of 1.</p>
<p class="muted small">Weights and thresholds are a judgement call, not an established index. Credit carries the most weight because debt-funded busts tend to break in the bond market before they break in stocks.</p>
</div></div>
<div class="tw" style="margin-top:16px"><table><thead><tr><th>Signal</th><th>Calm → breach</th><th>Now</th><th>Weight</th><th>Score</th></tr></thead><tbody>{clock_rows}</tbody></table></div>
</div>
</section>

<section id="gauges">
<h2>Where the stress is showing</h2>
<p class="sub">Red = active stress, amber = watch, green = calm. Each status is an assessment, not an official threshold. Each tile shows the date of its reading.</p>
<div class="tiles">{tiles}</div>
</section>

<section id="loop">
<h2>The loop, traced</h2>
<p class="sub">Reported money flows that circle between chipmakers, AI labs, cloud providers and their financiers.</p>
<div class="grid2">
<div class="card"><p style="margin:0">{e(note["imf"])}</p></div>
<div class="card">{table([("flow","Money flows"),("type","Type"),("amount","Size"),("note","Why it matters")], loop)}</div>
</div>
</section>

<section id="signals">
<h2>Warning signs to watch</h2>
<div class="card">{table([("signal","Signal"),("status","Now"),("why","Why it matters")], trig)}</div>
</section>

<section id="scenarios">
<h2>Downturn scenarios</h2>
<p class="sub">How far each group could fall in three scenarios. These bands are illustrative assumptions anchored to past busts, not forecasts. The lesson from 2008: in a forced-selling phase almost everything falls together, including gold miners; what differs is margin resilience and recovery speed.</p>
{scen_blocks}
<div class="card"><h3>What past busts did</h3><p class="muted small">Approximate peak-to-trough falls, rounded from market history.</p>
{table([("episode","Episode"),("asset","Asset"),("drawdown","Fall"),("lesson","Lesson")], hist)}</div>
</section>

<section id="about">
<h2>About this page</h2>
<div class="card warn">
<h3>General information only</h3>
<p>This site is general market commentary for information and education. It is not financial product advice and does not take into account your objectives, financial situation or needs. It does not recommend buying, selling or holding any financial product. Consider getting advice from a licensed financial adviser before making any investment decision. Past performance is not a reliable indicator of future performance.</p>
</div>
<div class="card">
<p>Figures are compiled from public reporting, with the source for each listed below, and are refreshed periodically, so they will lag live markets. Statuses, the clock's weights and thresholds, and the scenarios are judgements. Some readings (for example credit default swap levels) are published irregularly, so a tile may show an older date.</p>
<p>Research and drafting are done with Claude, an AI model made by Anthropic. Anthropic is one of the companies that appears in this data.</p>
</div>
</section>
</main>
<footer><div class="wrap">
<p><b>Sources for the gauges</b></p>
<ul>{sources}</ul>
<p>© {datetime.date.today().year} AI Contagion Watch · aicontagionwatch.com</p>
</div></footer>
</body>
</html>
'''
open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(page)
print(f'index.html written: {minutes:.1f} minutes to midnight (score {total:.3f})')
