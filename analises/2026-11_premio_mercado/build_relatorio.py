"""Gera relatorio_premio_mercado.html (versão por cidade) a partir de analise.json e cidades.json.
Rode antes: python3 analysis.py && python3 analysis_cidades.py"""
import json, html

A = json.load(open('analise.json', encoding='utf-8'))
C = json.load(open('cidades.json', encoding='utf-8'))
MES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out']
MLAB = {f'{i:02d}': MES[i-1] for i in range(1, 11)}
MLAB['11p'] = 'nov 1–17'
FLAB = {'2026-12': 'dez/26', '2027-01': 'jan/27', '2027-02': 'fev/27', '2027-03': 'mar/27'}
MINUS = '−'
CITIES = ['São Paulo', 'Florianópolis', 'Balneário Camboriú']
SLUG = {'São Paulo': 'sp', 'Florianópolis': 'fln', 'Balneário Camboriú': 'bc'}


# ------------------------------------------------------------------ formatação
def num(x, dec=1):
    s = f'{abs(x):,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return (MINUS if x < 0 and round(abs(x), dec) != 0 else '') + s

def sg(x, dec=1):
    if round(x, dec) == 0: return num(0, dec)
    return ('+' if x > 0 else MINUS) + num(abs(x), dec)

def prem(i, dec=1): return sg((i - 1) * 100, dec) + '%'
def dpp(a, b, dec=1): return sg((b - a) * 100, dec) + ' p.p.'
def yoy(a, b, dec=1): return sg((b / a - 1) * 100, dec) + '%'
def pct(x, dec=0): return num(x * 100, dec) + '%'
def brl(x): return 'R$ ' + num(x, 0)
def cls(v, thr=0.0): return 'pos' if v > thr else ('neg' if v < -thr else 'zero')
def short(b): return html.escape(b.split(' - ', 1)[0])
def long(b): return html.escape(b.split(' - ', 1)[1].strip() if ' - ' in b else b)
def P(x): return x['prem'] if x else None


# ------------------------------------------------------------------ peças reutilizáveis
def heat(a, b, kind):
    if kind == 'pp':
        v = (b - a) * 100; txt = sg(v, 1); s = v / 8
    else:
        v = (b / a - 1) * 100; txt = sg(v, 0) + '%'; s = v / 20
    if kind == 'neu':
        return f'<td class="num r hm neu">{txt}</td>'
    s = max(-1, min(1, s))
    return f'<td class="num r hm" style="--a:{abs(s)*42:.0f}%" data-t="{"pos" if s > 0 else "neg"}">{txt}</td>'


def line_chart(series, labels, aria):
    """series: {key: [valor ou None por mês]}; prêmio como índice"""
    months = list(MLAB.keys())
    vals = [v for s in series.values() for v in s if v is not None]
    lo = min(vals); hi = max(vals)
    ymin = min(0.9, (int((lo - 1) * 10) - 1) / 10 + 1) if lo < 1 else 1 + int((lo - 1) * 10) / 10 - 0.1
    ymin = max(ymin, 0.0)
    ymax = 1 + (int((hi - 1) * 10) + 1) / 10
    step = 0.1 if ymax - ymin <= 0.6 else (0.2 if ymax - ymin <= 1.2 else 0.5)
    W, H, L, R, T, B = 760, 280, 56, 118, 16, 32
    xs = lambda i: L + i * (W - L - R) / (len(months) - 1)
    ys = lambda v: T + (ymax - v) / (ymax - ymin) * (H - T - B)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{html.escape(aria)}">']
    t = ymin
    while t <= ymax + 1e-9:
        y = ys(t)
        g.append(f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" class="{"axis0" if abs(t-1) < 1e-9 else "grid"}"/>')
        g.append(f'<text x="{L-8}" y="{y+4:.1f}" class="tick" text-anchor="end">{prem(t,0)}</text>')
        t = round(t + step, 6)
    for i, m in enumerate(months):
        g.append(f'<text x="{xs(i):.1f}" y="{H-10}" class="tick" text-anchor="middle">{MLAB[m] if m != "11p" else "nov*"}</text>')
    ends = {}
    for k, vals_k in series.items():
        pts = [(i, v) for i, v in enumerate(vals_k) if v is not None]
        if not pts: continue
        # quebra a linha onde falta mês
        seg, segs = [], []
        for i, v in enumerate(vals_k):
            if v is None:
                if seg: segs.append(seg); seg = []
            else: seg.append((i, v))
        if seg: segs.append(seg)
        for sgm in segs:
            g.append(f'<polyline points="{" ".join(f"{xs(i):.1f},{ys(v):.1f}" for i, v in sgm)}" class="ln {k}"/>')
        for i, v in pts:
            tip = f'{labels[k]} · {MLAB[months[i]]}: prêmio {prem(v)}'
            g.append(f'<circle cx="{xs(i):.1f}" cy="{ys(v):.1f}" r="4" class="dot {k}"><title>{tip}</title></circle>')
            g.append(f'<circle cx="{xs(i):.1f}" cy="{ys(v):.1f}" r="11" class="hit"><title>{tip}</title></circle>')
        ends[k] = ys(pts[-1][1])
    prev = -99
    for k in sorted(ends, key=ends.get):
        y = max(ends[k], prev + 16); prev = y
        g.append(f'<text x="{W-R+10}" y="{y+4:.1f}" class="dlab">{labels[k]}</text>')
    g.append('</svg>')
    return '\n'.join(g)


def dumbbell(rows, ss_ref):
    W2, rowh, L2, R2, T2 = 760, 30, 190, 34, 30
    H2 = T2 + rowh * len(rows) + 30
    vals = [v for r in rows for v in (r['m1_3'], r['l3']['prem'])]
    xmin = min(0.6, min(vals) - 0.1); xmax = max(1.6, min(2.8, max(vals) + 0.1))
    xs2 = lambda v: L2 + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * (W2 - L2 - R2)
    g = [f'<svg viewBox="0 0 {W2} {H2}" role="img" aria-label="Prêmio dos prédios novos nos 3 primeiros meses e em ago–out 2026">']
    t = round(xmin * 5) / 5
    while t <= xmax + 1e-9:
        x = xs2(t)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T2-8}" y2="{H2-26}" class="{"axis0" if abs(t-1) < 1e-9 else "grid"}"/>')
        g.append(f'<text x="{x:.1f}" y="{H2-8}" class="tick" text-anchor="middle">{prem(t,0)}</text>')
        t = round(t + (0.2 if xmax - xmin < 1.5 else 0.4), 6)
    if ss_ref:
        x = xs2(ss_ref)
        g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T2-8}" y2="{H2-26}" class="ref"/>')
        g.append(f'<text x="{x+4:.1f}" y="{T2-14}" class="tick">same store ago–out/26: {prem(ss_ref,0)}</text>')
    g.append(f'<text x="{xs2(1.0)-4:.1f}" y="{T2-14}" class="tick" text-anchor="end">= mercado</text>')
    for j, r in enumerate(rows):
        y = T2 + j * rowh + rowh / 2
        a, b = r['m1_3'], r['l3']['prem']
        g.append(f'<text x="{L2-12}" y="{y+4:.1f}" class="rlab" text-anchor="end">{short(r["b"])} <tspan class="rsub">{r["first"][5:7]}/{r["first"][2:4]}</tspan></text>')
        g.append(f'<line x1="{xs2(a):.1f}" x2="{xs2(b):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="bar {"up" if b >= a else "dn"}"/>')
        tip = f'{short(r["b"])}: 3 primeiros meses {prem(a)} → ago–out/26 {prem(b)}'
        g.append(f'<circle cx="{xs2(a):.1f}" cy="{y:.1f}" r="5" class="dot y25"><title>{tip}</title></circle>')
        g.append(f'<circle cx="{xs2(b):.1f}" cy="{y:.1f}" r="6" class="dot new"><title>{tip}</title></circle>')
        g.append(f'<text x="{max(xs2(a), xs2(b)) + 10:.1f}" y="{y+4:.1f}" class="vlab">{prem(b,0)}{" ›" if b > xmax else ""}</text>')
    g.append('</svg>')
    return '\n'.join(g)


MET = [('occ', 'Ocupação', 'pp'), ('mbp', 'Diária fechada', '%'), ('p50', 'Preço anunciado (p50)', '%'),
       ('rp', 'RevPAR', '%'), ('tal', 'Oferta (anúncios)', 'neu'), ('dem', 'Noites vendidas', 'neu')]


def city_heat(cd):
    mon = cd['mkt']['monthly']; y = cd['mkt']['ytd']
    head = ''.join(f'<th class="r">{MLAB[r["m"]]}</th>' for r in mon)
    rows = []
    for k, lab, kind in MET:
        cells = ''.join(heat(r['g']['a'][k], r['g']['b'][k], kind) if r['g'] else '<td></td>' for r in mon)
        lvl = pct(y['b'][k]) if k == 'occ' else (brl(y['b'][k]) if k in ('mbp', 'p50', 'rp') else '')
        rows.append(f'<tr><td class="mlab">{lab}</td>{cells}{heat(y["a"][k], y["b"][k], kind).replace("hm", "hm ytd")}<td class="num r muted">{lvl}</td></tr>')
    return f'''<div class="tbl"><table class="t-city"><thead><tr><th>Métrica</th>{head}<th class="r">Jan–out</th><th class="r">Nível jan–out 26</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''


def sub_table(cd, cname):
    groups = [('Cidade inteira', cd['mkt'], None)] + [(s, v, v['codes']) for s, v in cd['subs'].items()]
    rows = []
    for lab, g, codes in groups:
        y = g['ytd']
        if not y: continue
        a, b = y['a'], y['b']
        f = lambda x: f'<td class="num r {cls(x["b"]["rp"]/x["a"]["rp"]-1, .02)}">{yoy(x["a"]["rp"], x["b"]["rp"], 0)}</td>' if x else '<td class="num r muted">–</td>'
        sub = f'<span class="bsub">{", ".join(codes)}</span>' if codes else f'<span class="bsub">{y["nb"]} prédios</span>'
        rows.append(f'''<tr class="{'em' if codes is None else ''}"><td><span class="bname">{html.escape(lab)}</span>{sub}</td>
<td class="num r">{pct(a['occ'])} → {pct(b['occ'])} <span class="{cls(b['occ']-a['occ'], .015)}">({sg((b['occ']-a['occ'])*100, 1)})</span></td>
<td class="num r {cls(b['mbp']/a['mbp']-1, .02)}">{yoy(a['mbp'], b['mbp'], 0)}</td>
<td class="num r">{yoy(a['p25'], b['p25'], 0)} · {yoy(a['p50'], b['p50'], 0)} · {yoy(a['p75'], b['p75'], 0)}</td>
<td class="num r b {cls(b['rp']/a['rp']-1, .02)}">{yoy(a['rp'], b['rp'], 0)}</td>
<td class="num r muted">{yoy(a['tal'], b['tal'], 0)}</td><td class="num r muted">{yoy(a['dem'], b['dem'], 0)}</td>
{f(g['ytd_wd'])}{f(g['ytd_we'])}{f(g['ago_out'])}{f(g['nov'])}</tr>''')
    return f'''<div class="tbl"><table class="t-sub"><thead><tr><th>Submercado</th><th class="r">Ocupação jan–out<br>25 → 26 (p.p.)</th><th class="r">Diária<br>fechada</th><th class="r">Preço anunciado<br>p25 · p50 · p75</th><th class="r">RevPAR<br>jan–out</th><th class="r">Oferta</th><th class="r">Noites<br>vendidas</th><th class="r">RevPAR<br>dom–qui</th><th class="r">RevPAR<br>sex–sáb</th><th class="r">RevPAR<br>ago–out</th><th class="r">RevPAR<br>nov 1–17</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''


def pace_table(cd):
    groups = [('Cidade inteira', cd['fwd'])] + list(cd['fwd_subs'].items())
    head = ''.join(f'<th class="r">{FLAB[m]}</th>' for m in FLAB)
    rows = []
    for lab, ff in groups:
        cells = ''
        for m in FLAB:
            x = ff.get(m)
            if not x: cells += '<td></td>'; continue
            d = (x['occ'] - x['stly']) * 100
            cells += f'<td class="num r">{pct(x["occ"])} <span class="muted">vs {pct(x["stly"])}</span> <span class="{cls(d, 1)}">({sg(d, 1)})</span></td>'
        dec = ff.get('2026-12')
        sup = yoy(dec['tal_ly'], dec['tal'], 0) if dec else ''
        rows.append(f'<tr class="{"em" if lab == "Cidade inteira" else ""}"><td class="bname">{html.escape(lab)}</td>{cells}<td class="num r muted">{sup}</td></tr>')
    return f'''<div class="tbl"><table class="t-pace"><thead><tr><th>Ocupação do mercado já vendida<br>hoje vs mesmo dia do ano passado</th>{head}<th class="r">Oferta dez<br>vs LY</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''


def wkd_table(cd):
    m = cd['mkt']
    rows = []
    for lab, k in (('Jan–out · dom–qui', 'ytd_wd'), ('Jan–out · sex–sáb', 'ytd_we'), ('Ago–out · dom–qui', 'ao_wd'), ('Ago–out · sex–sáb', 'ao_we')):
        x = m[k]; a, b = x['a'], x['b']
        rows.append(f'''<tr><td>{lab}</td><td class="num r">{pct(a['occ'])} → {pct(b['occ'])} <span class="{cls(b['occ']-a['occ'], .015)}">({sg((b['occ']-a['occ'])*100, 1)})</span></td>
<td class="num r">{brl(a['mbp'])} → {brl(b['mbp'])} <span class="{cls(b['mbp']/a['mbp']-1, .02)}">({yoy(a['mbp'], b['mbp'], 0)})</span></td>
<td class="num r b {cls(b['rp']/a['rp']-1, .02)}">{yoy(a['rp'], b['rp'], 1)}</td></tr>''')
    return f'''<div class="tbl"><table class="t-wk"><thead><tr><th>Noites</th><th class="r">Ocupação</th><th class="r">Diária fechada</th><th class="r">RevPAR</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>'''


def prem_table(cd, cname):
    p = cd['prem']
    def row(lab, a_key, b_key, em=False):
        if not p['ytd'][b_key]: return ''
        cells = ''
        for per in ('ytd', 'ago_out', 'out', 'nov'):
            a, b = P(p[per][a_key]) if a_key else None, P(p[per][b_key])
            if b is None: cells += '<td></td><td></td>'; continue
            cells += f'<td class="num r">{prem(a) if a else "–"} → <b>{prem(b)}</b></td>'
            cells += f'<td class="num r {cls(b-a, .005) if a else "muted"}">{dpp(a, b) if a else ""}</td>'
        return f'<tr class="{"em" if em else ""}"><td>{lab}</td>{cells}</tr>'
    r = ''
    if cd['ss']: r += row(f'Same store ({len(cd["ss"])} prédios)', 'ss25', 'ss26', True)
    if cd['new']: r += row(f'Prédios novos ({len([b for b in cd["new"] if b not in A["excl_ramp"]])} prédios)', None, 'new26')
    r += row('Total da cidade', 'all25', 'all26')
    return f'''<div class="tbl"><table class="t-prem"><thead><tr><th>Grupo</th><th class="r">Jan–out 25 → 26</th><th class="r">Δ</th><th class="r">Ago–out</th><th class="r">Δ</th><th class="r">Outubro</th><th class="r">Δ</th><th class="r">Nov 1–17</th><th class="r">Δ</th></tr></thead>
<tbody>{r}</tbody></table></div>'''


def ss_table(cname):
    t = []
    for r in sorted([r for r in A['ss_buildings'] if r['city'] == cname], key=lambda r: -(r['y26']['prem'] - r['y25']['prem'])):
        a, b, a3, b3, an, bn = r['y25'], r['y26'], r['r25'], r['r26'], r['n25'], r['n26']
        t.append(f'''<tr><td><span class="bname">{short(r['b'])}</span><span class="bsub">{long(r['b'])}</span></td>
<td class="num r">{num(r['u26'], 0)}</td>
<td class="num r">{prem(a['prem'], 0)} → <b>{prem(b['prem'], 0)}</b></td><td class="num r {cls(b['prem']-a['prem'], .02)}">{dpp(a['prem'], b['prem'], 0)}</td>
<td class="num r">{prem(a3['prem'], 0)} → {prem(b3['prem'], 0)}</td>
<td class="num r">{prem(an['prem'], 0)} → {prem(bn['prem'], 0)}</td>
<td class="num r">{yoy(a['revpar'], b['revpar'], 0)}</td><td class="num r">{yoy(a['mrevpar'], b['mrevpar'], 0)}</td>
<td class="num r">{pct(b3['occ'])} / {pct(b3['mo'])}</td><td class="num r">{num(a3['adr'], 0)} → {num(b3['adr'], 0)} / {num(b3['madr'], 0)}</td></tr>''')
    if not t: return ''
    return f'''<h3>Same store por prédio</h3><div class="tbl"><table class="t-ss">
<thead><tr><th>Prédio</th><th class="r">Unid.</th><th class="r">Prêmio jan–out<br>25 → 26</th><th class="r">Δ</th><th class="r">Ago–out<br>25 → 26</th><th class="r">Nov 1–17<br>25 → 26</th><th class="r">Nosso RevPAR<br>YoY</th><th class="r">RevPAR mercado<br>YoY</th><th class="r">Ocup. ago–out 26<br>nós / mercado</th><th class="r">Diária ago–out (R$)<br>nós 25 → 26 / mercado</th></tr></thead>
<tbody>{"".join(t)}</tbody></table></div>'''


def new_table(cname):
    rs = [r for r in A['ramp'] if r['city'] == cname and r['b'] not in A['excl_ramp']]
    t = []
    for r in sorted(rs, key=lambda r: r['first']):
        l = r['l3']
        cell = lambda v: f'<td class="num r">{prem(v, 0)}</td>' if v is not None else '<td class="num r muted">–</td>'
        t.append(f'''<tr><td><span class="bname">{short(r['b'])}</span><span class="bsub">{long(r['b'])}</span></td>
<td class="num">{r['first'][8:10]}/{r['first'][5:7]}/{r['first'][2:4]}</td><td class="num r">{num(r['ytd26']['n']/304, 0)}</td>
{cell(r['m1_3'])}{cell(r['m4_6'])}{cell(r['m7_12'])}<td class="num r b">{prem(l['prem'], 0)}</td>
<td class="num r">{pct(l['occ'])} / {pct(l['mo'])}</td><td class="num r">{num(l['adr'] or 0, 0)} / {num(l['madr'], 0)}</td></tr>''')
    if not t: return '', rs
    return f'''<div class="tbl"><table class="t-new"><thead><tr><th>Prédio</th><th>Entrada</th><th class="r">Unid. 26</th><th class="r">Meses 1–3</th><th class="r">Meses 4–6</th><th class="r">Meses 7–12</th><th class="r">Ago–out 26</th><th class="r">Ocup. ago–out<br>nós / mercado</th><th class="r">Diária ago–out (R$)<br>nós / mercado</th></tr></thead>
<tbody>{"".join(t)}</tbody></table></div>''', rs


def mkt_bld_table(cname):
    bs = [r for r in A['mkt_buildings'] if r['city'] == cname]
    bs.sort(key=lambda r: -(r['ytd']['b']['rp'] / r['ytd']['a']['rp']))
    t = []
    for r in bs:
        a, b = r['ytd']['a'], r['ytd']['b']
        f3 = (lambda g: f'<td class="num r {cls(g["b"]["rp"]/g["a"]["rp"]-1, .02)}">{yoy(g["a"]["rp"], g["b"]["rp"], 0)}</td>' if g else '<td class="num r muted">–</td>')
        nm = len(r['months'])
        base = 'jan–out' if nm == 10 else f'{MLAB[r["months"][0]]}–{MLAB[r["months"][-1]]}'
        t.append(f'''<tr><td><span class="bname">{short(r['b'])}</span><span class="bsub">{long(r['b'])}{'' if r['ss'] else ' · novo'}</span></td>
<td class="num">{base}</td>
<td class="num r">{pct(a['occ'])} → {pct(b['occ'])} <span class="{cls(b['occ']-a['occ'], .015)}">({sg((b['occ']-a['occ'])*100, 1)})</span></td>
<td class="num r {cls(b['mbp']/a['mbp']-1, .02)}">{yoy(a['mbp'], b['mbp'], 0)}</td><td class="num r">{yoy(a['p50'], b['p50'], 0)}</td>
<td class="num r b {cls(b['rp']/a['rp']-1, .02)}">{yoy(a['rp'], b['rp'], 0)}</td><td class="num r muted">{yoy(a['tal'], b['tal'], 0)}</td>
{f3(r['l3'])}{f3(r['nov'])}<td class="num r">{brl(b['rp'])}</td></tr>''')
    return f'''<div class="tbl"><table class="t-mkt"><thead><tr><th>Mercado do prédio</th><th>Base</th><th class="r">Ocupação 25 → 26</th><th class="r">Diária fechada</th><th class="r">Preço anunciado</th><th class="r">RevPAR</th><th class="r">Oferta</th><th class="r">RevPAR<br>ago–out</th><th class="r">RevPAR<br>nov 1–17</th><th class="r">RevPAR 26</th></tr></thead>
<tbody>{"".join(t)}</tbody></table></div>'''


# ------------------------------------------------------------------ números para os textos
def g(c, *path):
    x = C['cities'][c]
    for p in path: x = x[p]
    return x

def mk(c, per='ytd', sub=None):
    x = g(c, 'subs', sub, per) if sub else g(c, 'mkt', per)
    return x['a'], x['b']

def rpy(c, per='ytd', sub=None):
    a, b = mk(c, per, sub); return yoy(a['rp'], b['rp'])

def occd(c, per='ytd', sub=None):
    a, b = mk(c, per, sub); return sg((b['occ'] - a['occ']) * 100) + ' p.p.'

def adry(c, per='ytd', sub=None):
    a, b = mk(c, per, sub); return yoy(a['mbp'], b['mbp'])

def p50y(c, per='ytd', sub=None):
    a, b = mk(c, per, sub); return yoy(a['p50'], b['p50'])

def supy(c, per='ytd', sub=None):
    a, b = mk(c, per, sub); return yoy(a['tal'], b['tal'], 0)

def demy(c, per='ytd', sub=None):
    a, b = mk(c, per, sub); return yoy(a['dem'], b['dem'], 0)

def pr(c, per, k): return P(g(c, 'prem', per, k))

def fw(c, m, sub=None):
    x = g(c, 'fwd_subs', sub, m) if sub else g(c, 'fwd', m)
    return f'{pct(x["occ"])} vs {pct(x["stly"])}'

SP, FL, BC = CITIES
S_JD, S_PI, S_IT, S_VM, S_CE = list(C['cities'][SP]['subs'])
S_IN, S_FC = list(C['cities'][FL]['subs'])
fl_ss = {r['b'][:3]: r for r in A['ss_buildings'] if r['city'] == FL}
sp_ss_n = [r for r in A['ss_buildings'] if r['city'] == SP]
tso = [r for r in A['ramp'] if r['b'].startswith('TSO')][0]

# ------------------------------------------------------------------ textos por cidade
TXT = {}
TXT[SP] = dict(
    head=f'Prêmio same store estável no ano ({prem(pr(SP,"ytd","ss25"))} → {prem(pr(SP,"ytd","ss26"))}), queda forte só em nov 1–17',
    prem=[
        f'Nos {len(g(SP,"ss"))} prédios same store de SP o prêmio de jan–out subiu de {prem(pr(SP,"ytd","ss25"))} para {prem(pr(SP,"ytd","ss26"))} e ficou estável em ago–out ({prem(pr(SP,"ago_out","ss25"))} → {prem(pr(SP,"ago_out","ss26"))}). Outubro recuou pouco ({prem(pr(SP,"out","ss25"))} → {prem(pr(SP,"out","ss26"))}).',
        f'A queda está em nov 1–17: {prem(pr(SP,"nov","ss25"))} → {prem(pr(SP,"nov","ss26"))}. O mercado subiu a diária fechada {adry(SP,"nov")} e perdeu {occd(SP,"nov").replace(MINUS,"")} de ocupação; nossa ocupação same store caiu de {pct(g(SP,'prem','nov','ss25')['occ'])} para {pct(g(SP,'prem','nov','ss26')['occ'])} com a diária parada em {brl(g(SP,'prem','nov','ss26')['adr'])}. Ou seja, não acompanhamos a alta de preço do mercado e ainda perdemos mais ocupação que ele.',
        f'Os prédios novos de SP rodam com {prem(pr(SP,"ytd","new26"))} em jan–out e {prem(pr(SP,"ago_out","new26"))} em ago–out, acima do same store.',
    ],
    mkt=[
        f'RevPAR do mercado de SP em jan–out: {rpy(SP)}. A ocupação subiu {occd(SP)} e a diária fechada caiu {adry(SP).replace(MINUS,"")}, enquanto o preço anunciado subiu {p50y(SP)}. A oferta de anúncios no comp set cresceu {supy(SP)} e as noites vendidas {demy(SP)}: a demanda cresceu no mesmo ritmo da oferta, por isso a ocupação não caiu; a pressão apareceu no preço fechado.',
        f'Depois de setembro o mercado melhorou: RevPAR {rpy(SP,"ago_out")} em ago–out e {rpy(SP,"nov")} em nov 1–17, com diária fechada {adry(SP,"nov")} em novembro. O preço anunciado em nov 1–17 está {p50y(SP,"nov")} acima do ano passado.',
        f'Submercados: Itaim / Vila Nova / Vila Olímpia é o mais fraco ({rpy(SP,"ytd",S_IT)}, ocupação {occd(SP,"ytd",S_IT)}, diária {adry(SP,"ytd",S_IT)}). Centro / Higienópolis é o mais forte ({rpy(SP,"ytd",S_CE)}, com diária {adry(SP,"ytd",S_CE)}). Jardins / Paulista ficou em {rpy(SP,"ytd",S_JD)} no ano mas virou para {rpy(SP,"ago_out",S_JD)} em ago–out e {rpy(SP,"nov",S_JD)} em nov 1–17. Em Vila Mariana / Paraíso / Moema a oferta quase dobrou ({supy(SP,"ytd",S_VM)}) e a diária fechada caiu {adry(SP,"ytd",S_VM).replace(MINUS,"")}: parte disso é mudança do próprio comp set.',
        f'Semana e fim de semana andaram juntos em SP (RevPAR jan–out {rpy(SP,"ytd_wd")} dom–qui e {rpy(SP,"ytd_we")} sex–sáb).',
        f'Pace: hoje o mercado de SP tem {fw(SP,"2026-12")} de ocupação vendida para dez/26 contra o mesmo dia do ano passado, e {fw(SP,"2027-01")} para jan/27. Está no mesmo ritmo ou um pouco à frente, com muito mais oferta.',
    ])
TXT[FL] = dict(
    head=f'Prêmio same store caindo desde agosto ({prem(pr(FL,"ago_out","ss25"))} → {prem(pr(FL,"ago_out","ss26"))} em ago–out) e mercado mais fraco',
    prem=[
        f'Nos {len(g(FL,"ss"))} prédios same store de Florianópolis o prêmio de jan–out caiu de {prem(pr(FL,"ytd","ss25"))} para {prem(pr(FL,"ytd","ss26"))}, e a queda acelerou: ago–out {prem(pr(FL,"ago_out","ss25"))} → {prem(pr(FL,"ago_out","ss26"))}, outubro {prem(pr(FL,"out","ss25"))} → {prem(pr(FL,"out","ss26"))}, nov 1–17 {prem(pr(FL,"nov","ss25"))} → {prem(pr(FL,"nov","ss26"))}. Em outubro nossa ocupação same store aqui caiu de {pct(g(FL,'prem','out','ss25')['occ'])} para {pct(g(FL,'prem','out','ss26')['occ'])} e a diária de {brl(g(FL,'prem','out','ss25')['adr'])} para {brl(g(FL,'prem','out','ss26')['adr'])}, com o mercado perdendo bem menos ocupação.',
        f'O movimento é concentrado em Ingleses: em ago–out a diária de AQL caiu de {brl(fl_ss["AQL"]["r25"]["adr"])} para {brl(fl_ss["AQL"]["r26"]["adr"])}, a de AGM de {brl(fl_ss["AGM"]["r25"]["adr"])} para {brl(fl_ss["AGM"]["r26"]["adr"])} e a de CAN de {brl(fl_ss["CAN"]["r25"]["adr"])} para {brl(fl_ss["CAN"]["r26"]["adr"])}, enquanto a diária fechada do mercado de Ingleses subiu {adry(FL,"ago_out",S_IN)}; mesmo baixando preço, AQL e CAN perderam ocupação. CAN também aumentou o peso de mid-term (de {pct(fl_ss["CAN"]["y25"]["mt"])} para {pct(fl_ss["CAN"]["y26"]["mt"])} das noites em jan–out), o que puxa a diária para baixo.',
        f'Os prédios novos (FST e TBG) rodam com {prem(pr(FL,"ytd","new26"))} em jan–out.',
    ],
    mkt=[
        f'RevPAR do mercado de Florianópolis em jan–out: {rpy(FL)}. A queda veio da ocupação ({occd(FL)}), com diária fechada praticamente estável ({adry(FL)}). A oferta cresceu {supy(FL)} e as noites vendidas {demy(FL)}: aqui a demanda cresceu menos que a oferta.',
        f'Ingleses (praia) perdeu {occd(FL,"ytd",S_IN).replace(MINUS,"")} de ocupação no ano ({rpy(FL,"ytd",S_IN)} de RevPAR) com oferta {supy(FL,"ytd",S_IN)}. Em nov 1–17 o mercado de Ingleses subiu a diária {adry(FL,"nov",S_IN)} e perdeu {occd(FL,"nov",S_IN).replace(MINUS,"")} de ocupação.',
        f'Centro / Agronômica / Saco Grande caiu {rpy(FL,"ytd",S_FC).replace(MINUS,"")} no ano, mais por diária ({adry(FL,"ytd",S_FC)}) do que por ocupação ({occd(FL,"ytd",S_FC)}). O fim de semana pesou mais: RevPAR sex–sáb {rpy(FL,"ao_we",S_FC)} em ago–out contra {rpy(FL,"ao_wd",S_FC)} dom–qui. Em nov 1–17 virou: {rpy(FL,"nov",S_FC)}.',
        f'Pace do verão: para dez/26 o mercado de Florianópolis tem {fw(FL,"2026-12")} de ocupação vendida contra o mesmo dia do ano passado, ou seja, atrás. Em Ingleses, dez/26 está em {fw(FL,"2026-12",S_IN)} e jan/27 em {fw(FL,"2027-01",S_IN)}, também atrás. O Centro está à frente em jan/27 ({fw(FL,"2027-01",S_FC)}).',
    ])
a_bc, b_bc = mk(BC)
TXT[BC] = dict(
    head=f'Só TSO: prêmio alto e mercado estável, com o dobro da oferta',
    prem=[
        f'TSO é o único prédio em Balneário Camboriú (entrou em jun/25). Prêmio de ago–out {prem(pr(BC,"ago_out","all25"))} → {prem(pr(BC,"ago_out","all26"))}; nov 1–17 {prem(pr(BC,"nov","all25"))} → {prem(pr(BC,"nov","all26"))}. O jan–out de 2025 tem só jun–out, então use ago–out para comparar.',
        f'O nível de prêmio (acima de +100%) vem da diária muito acima da mediana do comp set de 2 quartos de BC: mede mais o encaixe do comp set do que o pricing.',
    ],
    mkt=[
        f'RevPAR do mercado de BC em jan–out: {rpy(BC)} (ocupação {occd(BC)}, diária fechada {adry(BC)}), com a oferta do comp set dobrando ({supy(BC)}). Em nov 1–17: RevPAR {rpy(BC,"nov")}, diária {adry(BC,"nov")} e ocupação {occd(BC,"nov")}',
        f'Pace do verão: dez/26 {fw(BC,"2026-12")} e jan/27 {fw(BC,"2027-01")}, no mesmo ritmo ou à frente do ano passado.',
    ])

# ------------------------------------------------------------------ montagem das seções
sections, kpis = [], []
for c in CITIES:
    cd = C['cities'][c]; slug = SLUG[c]
    ser = cd['prem_serie']
    if cd['ss']:
        lines = {'y25': [P(r['ss25']) for r in ser], 'y26': [P(r['ss26']) for r in ser]}
        labels = {'y25': 'Same store ’25', 'y26': 'Same store ’26'}
        if cd['new']:
            lines['new'] = [P(r['new26']) if r['new26'] and r['new26']['n'] >= 150 else None for r in ser]
            labels['new'] = 'Novos ’26'
    else:
        lines = {'y25': [P(r['all25']) if r['all25'] and r['all25']['n'] >= 150 else None for r in ser], 'y26': [P(r['all26']) for r in ser]}
        labels = {'y25': 'TSO ’25', 'y26': 'TSO ’26'}
    chart = line_chart(lines, labels, f'Prêmio mensal em {c}')
    newt, rs = new_table(c)
    ramp_rows = sorted([r for r in rs if r['m1_3'] and r['l3']], key=lambda r: -r['l3']['prem'])
    db = dumbbell(ramp_rows, P(cd['prem']['ago_out']['ss26']) if cd['ss'] else None) if len(ramp_rows) >= 3 else ''
    t = TXT[c]
    subs_html = ''
    if cd['subs']:
        subs_html = f'''<h3>Submercados</h3>
<p class="small">Variação jan–out 2026 vs 2025, salvo indicado. Ocupação em pontos percentuais; demais em %.</p>
{sub_table(cd, c)}'''
    sections.append(f'''
<section id="{slug}" class="city">
  <div class="sec-head"><span class="eyebrow">{html.escape(c)}</span><h2>{t['head']}</h2></div>
  <h3>Nosso prêmio</h3>
  <ul class="bul">{''.join(f'<li>{x}</li>' for x in t['prem'])}</ul>
  {prem_table(cd, c)}
  <div class="panel"><div class="legend"><span><i class="c25"></i>{labels['y25']}</span><span><i class="c26"></i>{labels['y26']}</span>{'<span><i class="cnew"></i>' + labels['new'] + ' (tracejado)</span>' if 'new' in labels else ''}<span>* nov = dias 1 a 17</span></div>{chart}</div>
  <h3>Mercado</h3>
  <ul class="bul">{''.join(f'<li>{x}</li>' for x in t['mkt'])}</ul>
  {city_heat(cd)}
  {subs_html}
  <div class="two">
    <div class="col"><h3>Semana × fim de semana</h3>{wkd_table(cd)}</div>
    <div class="col"><h3>Pace dos próximos meses</h3>{pace_table(cd)}</div>
  </div>
  {ss_table(c)}
  {('<h3>Prédios novos</h3>' + ('<div class="panel"><div class="legend"><span><i class="dt c25"></i>3 primeiros meses</span><span><i class="dt cnew"></i>Ago–out 2026</span><span>Linha tracejada laranja = same store da cidade em ago–out/26</span></div>' + db + '</div>' if db else '') + newt) if newt else ''}
  <h3>Mercado por prédio</h3>
  {mkt_bld_table(c)}
</section>''')
    y = cd['mkt']['ytd']
    if cd['ss']:
        main = f'{prem(pr(c,"ytd","ss26"))}'; sub1 = f'Same store jan–out (2025: {prem(pr(c,"ytd","ss25"))})'
        sub2 = f'Ago–out {prem(pr(c,"ago_out","ss25"),0)} → {prem(pr(c,"ago_out","ss26"),0)} · nov 1–17 {prem(pr(c,"nov","ss25"),0)} → {prem(pr(c,"nov","ss26"),0)}'
    else:
        main = f'{prem(pr(c,"ago_out","all26"))}'; sub1 = f'TSO ago–out (2025: {prem(pr(c,"ago_out","all25"))})'
        sub2 = f'Nov 1–17 {prem(pr(c,"nov","all25"),0)} → {prem(pr(c,"nov","all26"),0)}'
    kpis.append(f'''<a class="kpi" href="#{slug}"><span class="eyebrow">{html.escape(c)}</span>
<span class="v">{main}</span><span class="s">{sub1}</span><span class="s">{sub2}</span>
<span class="mk">Mercado jan–out: RevPAR <b>{yoy(y['a']['rp'], y['b']['rp'])}</b> · ocupação {sg((y['b']['occ']-y['a']['occ'])*100)} p.p. · diária {yoy(y['a']['mbp'], y['b']['mbp'])} · oferta {yoy(y['a']['tal'], y['b']['tal'], 0)}</span></a>''')

ssb = A['ss_blocks']
summary = [
    f'<b>Definição.</b> Prêmio = nosso RevPAR de hospedagem (<code>accommodation_adr</code>, diária sem taxas, zero nas noites não vendidas) ÷ RevPAR do mercado (diária mediana fechada do Pricelabs × ocupação do mercado). É a conta do dashboard 58.',
    f'<b>Same store no portfólio:</b> jan–out {prem(ssb["ytd"][0]["prem"])} → {prem(ssb["ytd"][1]["prem"])}; nov 1–17 {prem(ssb["nov"][0]["prem"])} → {prem(ssb["nov"][1]["prem"])}. Separando por cidade: SP ficou estável no ano e só caiu em nov 1–17; Florianópolis cai desde agosto. A queda de outubro do portfólio é quase toda de Florianópolis; em nov 1–17 as duas cidades caem.',
    f'<b>Mercados:</b> SP {rpy(SP)} de RevPAR no ano, com oferta e demanda crescendo juntas e pressão na diária fechada; melhora desde ago–out. Florianópolis {rpy(FL)}, por ocupação, com oferta crescendo mais que a demanda e verão vendendo atrás do ano passado. BC {rpy(BC)}.',
]

page = open('pagina.html', encoding='utf-8').read()
for k, v in dict(KPIS='\n'.join(kpis), SUMMARY='\n'.join(f'<li>{x}</li>' for x in summary), SECTIONS='\n'.join(sections),
                 EXCL_LIST=', '.join(short(b) for b in A['excl_ramp'])).items():
    page = page.replace('{{' + k + '}}', v)
assert '{{' not in page, page[page.index('{{'):page.index('{{') + 40]
open('relatorio_premio_mercado.html', 'w', encoding='utf-8').write(page)
print('ok', len(page))
