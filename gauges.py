"""Builds the Australian car-dashboard page (oz-gauges/index.html) and its shareable image (oz-gauges/oz-gauges.png).

Called from build.py with the clock score and the Australian exposure data. Inputs live in
data/gauges.json; data/clock_trail.json keeps one clock reading per day for the speed trend.
"""
import json, math, html, os, datetime

e = lambda s: html.escape(str(s))
clamp = lambda x: max(0.0, min(1.0, x))

SHORT = {'super': 'Super', 'inflation': 'Inflation', 'govt': 'Government AI bets',
         'critical': 'Critical industries', 'jobs': 'Jobs', 'wages': 'Wages vs prices'}
LIGHT = {'Stress': '#ef6a57', 'Watch': '#F2A93B', 'Calm': '#57b5a2'}


def today_melb():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo('Australia/Melbourne')).date()
    except Exception:
        return datetime.date.today()


def nice_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f'{d.day} {d.strftime("%B")}'


# ---------- drawing helpers (angles in degrees, clockwise from 12 o'clock)
def pt(cx, cy, r, a):
    t = math.radians(a)
    return cx + math.sin(t) * r, cy - math.cos(t) * r


def band(cx, cy, r0, r1, a0, a1):
    large = 1 if a1 - a0 > 180 else 0
    p1, p2, p3, p4 = pt(cx, cy, r1, a0), pt(cx, cy, r1, a1), pt(cx, cy, r0, a1), pt(cx, cy, r0, a0)
    return (f'M{p1[0]:.1f},{p1[1]:.1f} A{r1},{r1} 0 {large} 1 {p2[0]:.1f},{p2[1]:.1f} '
            f'L{p3[0]:.1f},{p3[1]:.1f} A{r0},{r0} 0 {large} 0 {p4[0]:.1f},{p4[1]:.1f} Z')


def dial(cx, cy, r, sweep, lo, hi, now, red_from, ticks, labels, readout, unit, status, status_col,
         extra='', big=False):
    a0, a1 = -sweep / 2, sweep / 2
    ang = lambda v: a0 + clamp((v - lo) / (hi - lo)) * sweep
    o = [f'<circle cx="{cx}" cy="{cy}" r="{r + 14}" class="k-face"/>',
         f'<path d="{band(cx, cy, r - 6, r, a0, a1)}" class="k-track"/>',
         f'<path d="{band(cx, cy, r - 10, r, ang(red_from), a1)}" class="k-red"/>']
    for v, major in ticks:
        a = ang(v)
        x1, y1 = pt(cx, cy, r - (22 if major else 14), a)
        x2, y2 = pt(cx, cy, r - 2, a)
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{"k-maj" if major else "k-min"}"/>')
    o.append(extra)
    na = ang(now)
    w = 7 if big else 5
    L = r - 12
    o.append(f'<g class="k-needle" style="--a:{na:.1f}deg;--from:{a0:.1f}deg;--o:{cx}px {cy}px" '
             f'transform="rotate({na:.1f} {cx} {cy})">'
             f'<polygon points="{cx - w},{cy + 18} {cx + w},{cy + 18} {cx + 1.5},{cy - L} {cx - 1.5},{cy - L}" class="k-ndl"/></g>'
             f'<circle cx="{cx}" cy="{cy}" r="{14 if big else 10}" class="k-hub"/>')
    for v, text, cls in labels:
        x, y = pt(cx, cy, r - (44 if big else 38), ang(v))
        o.append(f'<text x="{x:.1f}" y="{y + 6:.1f}" class="{cls} k-halo" text-anchor="middle">{e(text)}</text>')
    ry = cy + (78 if big else 62)
    o.append(f'<text x="{cx}" y="{ry}" text-anchor="middle" class="{"k-read-big" if big else "k-read"}">{e(readout)}</text>')
    if unit:
        o.append(f'<text x="{cx}" y="{ry + 24}" text-anchor="middle" class="k-unit">{e(unit)}</text>')
    o.append(f'<text x="{cx}" y="{ry + (52 if big else 30 if not unit else 50)}" text-anchor="middle" class="k-status" fill="{status_col}">{e(status)}</text>')
    return ''.join(o)


LAYOUTS = {
    'wide': dict(W=1200, H=630, hx=205, px=995, sx=600, side_y=300, sp_y=272, rs=118, rb=176,
                 sp_title=500, side_title=500, wrap=0, cols=6, pill_y=548, foot_y=614),
    'tall': dict(W=600, H=1130, hx=150, px=450, sx=300, side_y=730, sp_y=318, rs=104, rb=176,
                 sp_title=548, side_title=892, wrap=30, cols=2, pill_y=956, foot_y=1104),
}


def wrap(text, n):
    if not n or len(text) <= n:
        return [text]
    lines, cur = [], ''
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    return lines + [cur]


def cluster_svg(g, upd_label, layout='wide'):
    Lo = LAYOUTS[layout]
    W, H = Lo['W'], Lo['H']
    hx, px, sx = Lo['hx'], Lo['px'], Lo['sx']
    side_y, sp_y, rs, rb = Lo['side_y'], Lo['sp_y'], Lo['rs'], Lo['rb']
    gid = 'glow-' + layout
    heat, pres, spd = g['heat'], g['pres'], g['speed']

    heat_ticks = [(v, v % 5 == 0) for v in [20 + 2.5 * i for i in range(11)]]
    ref = heat['reference']
    ref_a = -110 + clamp((ref['value'] - heat['cold']) / (heat['hot'] - heat['cold'])) * 220
    rx1, ry1 = pt(hx, side_y, rs - 26, ref_a); rx2, ry2 = pt(hx, side_y, rs + 2, ref_a)
    tx, ty = pt(hx, side_y, rs - 34, ref_a)
    ref_mark = (f'<line x1="{rx1:.1f}" y1="{ry1:.1f}" x2="{rx2:.1f}" y2="{ry2:.1f}" class="k-ref"/>'
                f'<text x="{tx + 2:.1f}" y="{ty + 8:.1f}" class="k-reftxt" text-anchor="start">{e(ref["label"])}</text>')
    heat_dial = dial(hx, side_y, rs, 220, heat['cold'], heat['hot'], heat['now'], heat['redline'], heat_ticks,
                     [(heat['cold'], 'C', 'k-end'), (heat['hot'], 'H', 'k-end')],
                     heat['display'], '', heat['status'], heat['col'], ref_mark)

    pres_ticks = [(v, v % 25 == 0) for v in range(0, 101, 5)]
    pres_dial = dial(px, side_y, rs, 220, 0, 100, pres['score'], pres['redline'], pres_ticks,
                     [(0, 'Low', 'k-end-s'), (100, 'High', 'k-end-s')],
                     f'{pres["score"]:.0f}', '', pres['status'], pres['col'])

    sp_ticks = [(v, v % 20 == 0) for v in range(0, spd['max'] + 1, 10)]
    sp_labels = [(v, str(v), 'k-num') for v in range(0, spd['max'] + 1, 20)]
    sp_dial = dial(sx, sp_y, rb, 240, 0, spd['max'], spd['now'], spd['limit'], sp_ticks, sp_labels,
                   f'{spd["now"]:.0f}', 'km/h', spd['status'], spd['col'], big=True)

    titles = ''
    for x, ty0, t, q, wr in [(hx, Lo['side_title'], heat['title'], heat['question'], Lo['wrap']),
                             (sx, Lo['sp_title'], spd['title'], spd['question'], 0),
                             (px, Lo['side_title'], pres['title'], pres['question'], Lo['wrap'])]:
        titles += f'<text x="{x}" y="{ty0}" text-anchor="middle" class="k-title">{e(t)}</text>'
        for i, line in enumerate(wrap(q, wr)):
            titles += f'<text x="{x}" y="{ty0 + 22 + i * 19}" text-anchor="middle" class="k-q">{e(line)}</text>'

    pills, gap, cols = [], 10, Lo['cols']
    w = (W - 88 - gap * (cols - 1)) / cols
    for i, it in enumerate(g['lights']):
        col = LIGHT.get(it['status'], '#57b5a2')
        x = 44 + (i % cols) * (w + gap)
        y = Lo['pill_y'] + (i // cols) * 42
        pills.append(f'<g><rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="32" rx="16" class="k-pill"/>'
                     f'<circle cx="{x + 18:.1f}" cy="{y + 16}" r="6" fill="{col}" filter="url(#{gid})"/>'
                     f'<text x="{x + 32:.1f}" y="{y + 21}" class="k-pilltxt"><title>{e(it["factor"])}: {e(it["status"])}</title>{e(SHORT.get(it["id"], it["factor"]))}</text></g>')

    style = '''
.k-bg{fill:#0b2131}.k-face{fill:#10293b;stroke:#1f4560;stroke-width:2}
.k-track{fill:rgba(255,255,255,.10)}.k-red{fill:#d8432f}
.k-maj{stroke:#e6eef3;stroke-width:3;stroke-linecap:round}.k-min{stroke:#6f8ba0;stroke-width:1.6;stroke-linecap:round}
.k-ref{stroke:#F2A93B;stroke-width:3;stroke-dasharray:3 3}
text{font-family:Archivo,Inter,"Helvetica Neue",Arial,sans-serif;font-variant-numeric:tabular-nums}
.k-reftxt{fill:#F2A93B;font-size:12px;font-weight:600}
.k-halo{paint-order:stroke;stroke:#10293b;stroke-width:6px;stroke-linejoin:round}
.k-num{fill:#c9d6df;font-size:17px;font-weight:600}.k-end{fill:#e6eef3;font-size:20px;font-weight:700}
.k-end-s{fill:#c9d6df;font-size:13px;font-weight:600}
.k-ndl{fill:#F2A93B}.k-hub{fill:#0b2131;stroke:#F2A93B;stroke-width:4}
.k-read{fill:#fff;font-size:38px;font-weight:700;letter-spacing:-.5px}
.k-tall .k-read{font-size:31px}
.k-read-big{fill:#fff;font-size:60px;font-weight:800;letter-spacing:-1px}
.k-unit{fill:#9fb3c3;font-size:16px;font-weight:500}.k-status{font-size:15px;font-weight:700}
.k-title{fill:#fff;font-size:20px;font-weight:700}.k-q{fill:#9fb3c3;font-size:14.5px}
.k-h1{fill:#fff;font-size:26px;font-weight:800;letter-spacing:-.3px}.k-sub{fill:#9fb3c3;font-size:14px}
.k-pill{fill:#10293b;stroke:#1f4560}.k-pilltxt{fill:#dfe8ee;font-size:13.5px;font-weight:600}
.k-foot{fill:#7f97aa;font-size:12.5px}'''
    return (f'<svg class="k-svg k-{layout}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="Australia’s AI dashboard. Engine temperature {e(heat["display"])}, {e(heat["status"])}. '
            f'Speed {spd["now"]:.0f} kilometres an hour, {e(spd["status"])}. Oil pressure {pres["score"]:.0f} out of 100, {e(pres["status"])}.">'
            f'<style>{style}</style>'
            f'<defs><filter id="{gid}" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="3" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
            f'<rect width="{W}" height="{H}" rx="0" class="k-bg"/>'
            f'<text x="44" y="54" class="k-h1">Australia’s AI dashboard</text>'
            f'<text x="44" y="78" class="k-sub">Updated {e(upd_label)}</text>'
            f'{heat_dial}{pres_dial}{sp_dial}{titles}{"".join(pills)}'
            f'<text x="44" y="{Lo["foot_y"]}" class="k-foot">General information only, not financial advice.</text>'
            f'<text x="{W - 44}" y="{Lo["foot_y"]}" text-anchor="end" class="k-foot">aicontagionwatch.com/oz-gauges</text>'
            f'</svg>')


def compute(root, total, minutes, au):
    D = os.path.join(root, 'data')
    cfg = json.load(open(os.path.join(D, 'gauges.json'), encoding='utf-8'))

    h = dict(cfg['heat'])
    hf = clamp((h['now'] - h['cold']) / (h['hot'] - h['cold']))
    hot = h['now'] >= h['redline']
    h['status'] = 'Running hot' if hot else 'Warm' if hf >= 0.4 else 'Normal'
    h['col'] = '#ef6a57' if hot else '#F2A93B' if hf >= 0.4 else '#57b5a2'

    p = dict(cfg['pressure'])
    for i in p['inputs']:
        i['score'] = clamp((i['now'] - i['low']) / (i['high'] - i['low']))
    p['score'] = 100 * sum(i['score'] * i['weight'] for i in p['inputs']) / sum(i['weight'] for i in p['inputs'])
    p['status'] = 'Over pressure' if p['score'] >= p['redline'] else 'High' if p['score'] >= 50 else 'Normal'
    p['col'] = '#ef6a57' if p['score'] >= p['redline'] else '#F2A93B' if p['score'] >= 50 else '#57b5a2'

    s = dict(cfg['speed'])
    n = len(au) or 1
    stress = sum(1 for r in au if r['status'] == 'Stress')
    watch = sum(1 for r in au if r['status'] == 'Watch')
    s['au_index'] = (stress + 0.5 * watch) / n
    s['stress'], s['watch'], s['n'] = stress, watch, len(au)
    s['now'] = s['max'] * total * (0.5 + 0.5 * s['au_index'])
    s['status'] = 'Over the limit' if s['now'] >= s['limit'] else 'Picking up speed' if s['now'] >= 60 else 'Cruising'
    s['col'] = '#ef6a57' if s['now'] >= s['limit'] else '#F2A93B' if s['now'] >= 60 else '#57b5a2'

    # clock trail: one reading per Melbourne day, used for the trend line
    tp = os.path.join(D, 'clock_trail.json')
    trail = json.load(open(tp, encoding='utf-8')) if os.path.exists(tp) else []
    today = today_melb().isoformat()
    trail = [t for t in trail if t['date'] != today] + [{'date': today, 'minutes': round(minutes, 1)}]
    trail.sort(key=lambda t: t['date'])
    with open(tp, 'w', encoding='utf-8') as f:
        f.write('[\n' + ',\n'.join(' ' + json.dumps(t) for t in trail) + '\n]\n')
    cutoff = (today_melb() - datetime.timedelta(days=35)).isoformat()
    window = [t for t in trail if t['date'] >= cutoff and t['date'] != today]
    base = window[0] if window else (trail[0] if len(trail) > 1 else None)
    if base:
        d = base['minutes'] - round(minutes, 1)
        when = nice_date(base['date'])
        if d >= 0.1:
            s['trend'] = f'Speeding up: the clock has moved {d:.1f} minutes closer to midnight since {when}.'
        elif d <= -0.1:
            s['trend'] = f'Easing off: the clock has moved {-d:.1f} minutes further from midnight since {when}.'
        else:
            s['trend'] = f'Holding steady: the clock is where it was on {when}.'
    else:
        s['trend'] = ''
    return {'heat': h, 'pres': p, 'speed': s, 'lights': au, 'total': total, 'minutes': minutes}


PAGE_CSS = '''
:root{--navy:#0f2a3d;--deep:#0b2131;--fog:#eef1f3;--paper:#fff;--ink:#15212b;--slate:#56636e;--rule:#d3dae0;
--signal:#d8432f;--amber:#b77b07;--on-navy:#eaf0f4;--on-navy-dim:#9fb3c3;
--sans:"Archivo","Helvetica Neue",Arial,sans-serif;--serif:"Source Serif 4",Georgia,serif}
@media (prefers-color-scheme:dark){:root{--fog:#0c1c28;--paper:#11273a;--ink:#e3eaef;--slate:#9fb0bd;--rule:#244055;--amber:#e0a83a}}
*{box-sizing:border-box}body{margin:0;background:var(--fog);color:var(--ink);font:400 16px/1.5 var(--sans)}
a{color:inherit}:focus-visible{outline:3px solid var(--signal);outline-offset:2px}
.w{max-width:1160px;margin:0 auto;padding:0 20px}
.mast{background:var(--deep);color:var(--on-navy);padding-bottom:36px}
.bar{display:flex;align-items:center;gap:20px;height:56px;border-bottom:1px solid rgba(255,255,255,.12)}
.logo{display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:700;font-variation-settings:"wdth" 112;font-size:17px;white-space:nowrap}
.logo svg{width:24px;height:24px}.bar nav{margin-left:auto;display:flex;gap:20px}
.bar nav a{color:var(--on-navy-dim);text-decoration:none;font-size:14px;white-space:nowrap}.bar nav a:hover{color:#fff}
h1{font-size:clamp(28px,4vw,40px);line-height:1.1;font-weight:800;font-variation-settings:"wdth" 115;letter-spacing:-.02em;margin:36px 0 10px;color:#fff}
.lede{font-family:var(--serif);font-size:clamp(17px,1.7vw,19px);line-height:1.55;color:var(--on-navy);max-width:40em;margin:0 0 24px}
.cluster{border-radius:14px;overflow:hidden;border:1px solid #1f4560;box-shadow:0 0 0 6px rgba(255,255,255,.03)}
.k-svg{display:block;width:100%;height:auto}.k-tall{display:none}
@media (max-width:640px){.k-wide{display:none}.k-tall{display:block}.bar nav a+a{display:none}}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.mast .cluster{margin-top:28px}.lede{margin-top:20px}
.k-needle{transform-box:view-box;transform-origin:var(--o)}
@media (prefers-reduced-motion:no-preference){.k-needle{animation:k-sweep 1.8s cubic-bezier(.2,.8,.2,1) .25s both}
@keyframes k-sweep{from{transform:rotate(var(--from))}to{transform:rotate(var(--a))}}}
.trend{margin:16px 0 0;color:var(--on-navy);font-size:15px}
.trend b{color:#F2A93B}
main section{padding:48px 0 8px}
h2{font-size:clamp(22px,2.6vw,28px);font-weight:700;font-variation-settings:"wdth" 108;letter-spacing:-.015em;margin:0 0 8px}
.intro{font-family:var(--serif);font-size:17px;line-height:1.6;color:var(--slate);max-width:40em;margin:0 0 24px}
.dials{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.d{background:var(--paper);border:1px solid var(--rule);border-radius:6px;padding:20px 22px;display:flex;flex-direction:column}
.d h3{margin:0;font-size:19px;font-weight:700}.d .q{margin:2px 0 12px;color:var(--slate);font-size:14.5px}
.d .v{font-size:30px;font-weight:800;font-variation-settings:"wdth" 118;letter-spacing:-.02em;line-height:1.1;margin:0}
.d .st{font-weight:700;font-size:14px;margin:4px 0 0}
.d p.t{font-family:var(--serif);font-size:16px;line-height:1.6;margin:14px 0 0}
.d ul{margin:12px 0 0;padding:0;list-style:none;font-size:14.5px}
.d li{display:flex;justify-content:space-between;gap:12px;padding:7px 0;border-top:1px solid var(--rule)}
.d li span:last-child{font-weight:650;white-space:nowrap;font-variant-numeric:tabular-nums}
.d .src{margin:auto 0 0;padding-top:14px;font-size:12.5px;color:var(--slate)}
.share{display:grid;grid-template-columns:1fr 1fr;gap:40px}
.share p,.notice p{font-family:var(--serif);font-size:16.5px;line-height:1.6;margin:0 0 12px}
.btn{display:inline-block;background:var(--navy);color:#fff;text-decoration:none;font-weight:650;padding:10px 16px;border-radius:6px}
.notice{background:var(--paper);border:1px solid var(--rule);border-left:4px solid var(--amber);padding:20px 22px;border-radius:4px}
.notice h3,.share h3{margin:0 0 10px;font-size:18px}
footer{background:var(--deep);color:var(--on-navy-dim);margin-top:64px;padding:32px 0 40px;font-size:13.5px}
@media (max-width:860px){.dials,.share{grid-template-columns:1fr}}
'''

LOGO = ('<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="14.5" fill="none" stroke="#fff" '
        'stroke-opacity=".5" stroke-width="1.5"/><path d="M16 16 L5.2 9.8 A12.5 12.5 0 0 1 16 3.5 Z" fill="#d8432f"/>'
        '<path d="M16 17V6M16 16l-7-4" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/></svg>')


def page_html(g, svg, svg_tall, upd_label, asof):
    h, p, s = g['heat'], g['pres'], g['speed']
    stress, watch, n = s['stress'], s['watch'], s['n']
    calm = n - stress - watch
    lights_txt = f'{stress} at Stress, {watch} at Watch' + (f', {calm} Calm' if calm else '')
    pin = ''.join(f'<li><span>{e(i["label"])} ({e(i["asof"])})</span><span>{e(i["display"])}</span></li>' for i in p['inputs'])
    psrc = '; '.join(f'{i["label"]}: {i["source"]}' for i in p['inputs'])
    trend = f'<p class="trend"><b>{e(s["trend"].split(":")[0])}:</b>{e(s["trend"].split(":", 1)[1])}</p>' if s['trend'] else ''
    desc = (f'Engine temperature {h["display"]} ({h["status"].lower()}), speed {s["now"]:.0f} km/h '
            f'({s["status"].lower()}), oil pressure {p["score"]:.0f}/100. Australia’s exposure to the AI boom, as a car dashboard.')
    return f'''<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Australia’s AI dashboard: {s["now"]:.0f} km/h</title>
<meta name="description" content="{e(desc)}">
<meta property="og:title" content="Australia’s AI dashboard">
<meta property="og:description" content="{e(desc)}">
<meta property="og:type" content="website">
<meta property="og:url" content="https://aicontagionwatch.com/oz-gauges/">
<meta property="og:image" content="https://aicontagionwatch.com/oz-gauges/oz-gauges.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Car-style dashboard with gauges for AI market heat, risk speed and inflation pressure in Australia">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0b2131">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='15' fill='%230f2a3d'/%3E%3Cpath d='M16 16 L5.2 9.8 A12.5 12.5 0 0 1 16 3.5 Z' fill='%23d8432f'/%3E%3Cpath d='M16 17V6M16 16l-7-4' stroke='%23fff' stroke-width='2.4' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="mast"><div class="w">
<div class="bar"><a class="logo" href="/">{LOGO}AI Contagion Watch</a>
<nav aria-label="Site"><a href="/">Clock</a><a href="/#australia">Australian exposure</a></nav></div>
<h1 class="sr">Australia’s AI dashboard</h1>
<div class="cluster">{svg}{svg_tall}</div>
{trend}
<p class="lede">Three dials for how exposed Australia is to the AI boom, and to a bust. Heat is how much of the market rides on AI, speed is how fast the risk is building, and pressure is how hard inflation is squeezing the money AI runs on. The warning lights are the six areas where a bust would reach us.</p>
</div></div>

<main class="w">
<section id="dials">
<h2>Reading the dials</h2>
<p class="intro">Updated {e(upd_label)}{(", " + e(asof)) if asof else ""}. The scales and weightings are my own judgement calls, not an established index, so read the dials as direction rather than precision.</p>
<div class="dials">
<article class="d"><h3>{e(h["title"])}</h3><p class="q">{e(h["question"])}</p>
<p class="v">{e(h["display"])}</p><p class="st" style="color:{h["col"] if h["col"] != "#F2A93B" else "var(--amber)"}">{e(h["status"])}</p>
<p class="t">The share of the US share market held by its 10 biggest companies, nearly all of them riding on AI. It matters here because Australian super funds keep roughly 31% of members’ money in overseas shares, much of it in the US, so the more that market leans on a handful of AI companies, the hotter super’s engine runs.</p>
<ul><li><span>Cold, the 1990–2015 norm</span><span>about {h["cold"]}%</span></li><li><span>The 2000 dot-com peak</span><span>about {h["reference"]["value"]}%</span></li><li><span>Red line</span><span>{h["redline"]}%</span></li></ul>
<p class="src">As at {e(h["asof"])}. Source: {e(h["source"])}.</p></article>

<article class="d"><h3>{e(s["title"])}</h3><p class="q">{e(s["question"])}</p>
<p class="v">{s["now"]:.0f} km/h</p><p class="st" style="color:{s["col"] if s["col"] != "#F2A93B" else "var(--amber)"}">{e(s["status"])}</p>
<p class="t">Starts from how far the AI Contagion Watch clock has travelled towards midnight, then adds weight for how widely Australia is exposed right now, using the six warning lights. More risk, more speed. Past {s["limit"]} km/h, the open-road limit, the clock is in its high-fragility zone and the exposure is broad.</p>
<ul><li><span>Clock</span><span>{g["minutes"]:.1f} min to midnight</span></li><li><span>Warning lights</span><span>{e(lights_txt)}</span></li></ul>
<p class="src">Speed = {s["max"]} × clock score × (0.5 + 0.5 × share of lights on, with Watch counted as half). See the <a href="/">clock</a> and <a href="/#australia">Australian exposure</a> for the inputs.</p></article>

<article class="d"><h3>{e(p["title"])}</h3><p class="q">{e(p["question"])}</p>
<p class="v">{p["score"]:.0f} / 100</p><p class="st" style="color:{p["col"] if p["col"] != "#F2A93B" else "var(--amber)"}">{e(p["status"])}</p>
<p class="t">AI data centres are increasingly built on borrowed money, including loans and bonds that circle back to the same few companies. Inflation keeps interest rates high, and high rates make that debt dearer to carry and harder to refinance. This dial blends four readings, the bond yield counting most.</p>
<ul>{pin}</ul>
<p class="src">Each reading is scored from calm to stressed, then weighted 35/20/20/25 in the order listed. Sources: {e(psrc)}.</p></article>
</div>
</section>

<section id="share">
<div class="share">
<div><h3>Share it</h3>
<p>Today’s dashboard is saved as an image each time the site updates. Paste this page’s link into a post to show it as a preview card, or download the image to drop it in directly.</p>
<a class="btn" href="oz-gauges.png" download="australia-ai-dashboard.png">Download today’s image</a></div>
<div class="notice"><h3>General information only</h3>
<p>This page is general commentary for information and education. It is not financial product advice and does not take into account your objectives, financial situation or needs. Claude, an AI model, is used to research and generate this data. Claude is owned by Anthropic, one of the key players in the AI financing boom this site tracks.</p></div>
</div>
</section>
</main>
<footer><div class="w">© {datetime.date.today().year} AI Contagion Watch. General information only, not financial advice.</div></footer>
</body>
</html>
'''


def render_png(svg, path):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as ex:
        print('oz-gauges.png skipped (no Playwright):', ex)
        return
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1200, 'height': 630}, device_scale_factor=2)
        sized = svg.replace('class="k-svg"', 'class="k-svg" width="1200" height="630"', 1)
        pg.set_content('<html><body style="margin:0">' + sized + '</body></html>')
        pg.wait_for_timeout(300)
        pg.screenshot(path=path, clip={'x': 0, 'y': 0, 'width': 1200, 'height': 630})
        b.close()


def build(root, total, minutes, au, upd_label, asof):
    g = compute(root, total, minutes, au)
    svg = cluster_svg(g, upd_label)
    out = os.path.join(root, 'oz-gauges')
    os.makedirs(out, exist_ok=True)
    svg_tall = cluster_svg(g, upd_label, 'tall')
    open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(page_html(g, svg, svg_tall, upd_label, asof))
    render_png(svg, os.path.join(out, 'oz-gauges.png'))
    print(f'gauges written: heat {g["heat"]["display"]}, speed {g["speed"]["now"]:.0f} km/h, '
          f'pressure {g["pres"]["score"]:.0f}/100')
    return g
