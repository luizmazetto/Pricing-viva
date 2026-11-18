"""Gera relatorio_premio_mercado.html a partir de analise.json (rode analysis.py antes)."""
import json, html

d = json.load(open('analise.json', encoding='utf-8'))
MES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov']
MLAB = {f'{i:02d}': MES[i-1] for i in range(1, 11)}
MLAB['11p'] = 'nov 1–17'
CITY_SHORT = {'São Paulo': 'SP', 'Florianópolis': 'FLN', 'Balneário Camboriú': 'BC'}
MINUS = '−'


def num(x, dec=1):
    s = f'{abs(x):,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return (MINUS if x < 0 else '') + s


def sg(x, dec=1):
    """número com sinal"""
    if round(x, dec) == 0:
        return num(0, dec)
    return ('+' if x > 0 else MINUS) + num(abs(x), dec)


def prem(i, dec=1):
    """índice de prêmio (1,143) -> '+14,3%'"""
    return sg((i - 1) * 100, dec) + '%'


def dpp(a, b, dec=1):
    """variação do prêmio em pontos percentuais"""
    return sg((b - a) * 100, dec) + ' p.p.'


def yoy(a, b, dec=1):
    return sg((b / a - 1) * 100, dec) + '%'


def pct(x, dec=0):
    return num(x * 100, dec) + '%'


def brl(x):
    return 'R$ ' + num(x, 0)


def cls(v, thr=0.0):
    return 'pos' if v > thr else ('neg' if v < -thr else 'zero')


def short(b):
    return html.escape(b.split(' - ', 1)[0])


def long(b):
    return html.escape(b.split(' - ', 1)[1].strip() if ' - ' in b else b)


SS = d['meta']['SS']
ssb = d['ss_blocks']
allb = d['all_blocks']
new26 = d['new_ytd26']
city = d['meta']['city']

# ---------------------------------------------------------------- números-chave
ss_y25, ss_y26 = ssb['ytd']
ss_o25, ss_o26 = ssb['out']
ss_n25, ss_n26 = ssb['nov']
all_y25, all_y26 = allb['ytd']
n_new = len([r for r in d['ramp'] if r['b'] not in d['excl_ramp']])


def city_ytd(rows):
    rows = [r for r in rows if r['m'] != '11p']
    a = {k: sum(r['a'][k] for r in rows) / len(rows) for k in ('occ', 'mbp', 'p50', 'rp', 'tal')}
    b = {k: sum(r['b'][k] for r in rows) / len(rows) for k in ('occ', 'mbp', 'p50', 'rp', 'tal')}
    return a, b


cy = {c: city_ytd(rows) for c, rows in d['mkt_city'].items()}
tot_a, tot_b = cy['Total']
sp_out = [r for r in d['mkt_city']['São Paulo'] if r['m'] == '10'][0]

ramp_ok = [r for r in d['ramp'] if r['b'] not in d['excl_ramp'] and r['m1_3'] and r['l3']]
ramp_up = sum(1 for r in ramp_ok if r['l3']['prem'] > r['m1_3'])
nov_down = sum(1 for r in d['ss_buildings'] if r['n26']['prem'] < r['n25']['prem'])

# ---------------------------------------------------------------- gráfico 1: prêmio mensal
W, H, L, R, T, B = 760, 300, 52, 112, 18, 34
months = list(MLAB.keys())
ser = {r['m']: r for r in d['serie']}
lines = {
    'y25': [ser[f'2025-{m}']['ss']['prem'] for m in months],
    'y26': [ser[f'2026-{m}']['ss']['prem'] for m in months],
    'new': [ser[f'2026-{m}']['new']['prem'] for m in months],
}
ymin, ymax = 0.95, 1.40
xs = lambda i: L + i * (W - L - R) / (len(months) - 1)
ys = lambda v: T + (ymax - v) / (ymax - ymin) * (H - T - B)
g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Prêmio de RevPAR mensal: same store 2025, same store 2026 e prédios novos 2026">']
for t in [1.0, 1.1, 1.2, 1.3, 1.4]:
    y = ys(t)
    g.append(f'<line x1="{L}" x2="{W-R}" y1="{y:.1f}" y2="{y:.1f}" class="{"axis0" if t == 1.0 else "grid"}"/>')
    g.append(f'<text x="{L-8}" y="{y+4:.1f}" class="tick" text-anchor="end">{prem(t,0)}</text>')
for i, m in enumerate(months):
    g.append(f'<text x="{xs(i):.1f}" y="{H-12}" class="tick" text-anchor="middle">{MLAB[m] if m != "11p" else "nov*"}</text>')
labels = {'y25': 'Same store 2025', 'y26': 'Same store 2026', 'new': 'Prédios novos 2026'}
lab_y = {}
for k, vals in lines.items():
    pts = ' '.join(f'{xs(i):.1f},{ys(v):.1f}' for i, v in enumerate(vals))
    g.append(f'<polyline points="{pts}" class="ln {k}"/>')
    for i, v in enumerate(vals):
        tip = f'{labels[k]} · {MLAB[months[i]]}: prêmio {prem(v)}'
        g.append(f'<circle cx="{xs(i):.1f}" cy="{ys(v):.1f}" r="4" class="dot {k}"><title>{tip}</title></circle>')
        g.append(f'<circle cx="{xs(i):.1f}" cy="{ys(v):.1f}" r="11" class="hit"><title>{tip}</title></circle>')
    lab_y[k] = ys(vals[-1])
# rótulos diretos à direita, sem colisão
order = sorted(lab_y, key=lab_y.get)
prev = -99
for k in order:
    y = max(lab_y[k], prev + 16)
    prev = y
    g.append(f'<text x="{W-R+10}" y="{y+4:.1f}" class="dlab">{labels[k].replace(" 202", " ’2")}</text>')
g.append('</svg>')
chart1 = '\n'.join(g)

# ---------------------------------------------------------------- gráfico 2: halteres de ramp-up
rows = sorted(ramp_ok, key=lambda r: -r['l3']['prem'])
W2, rowh, L2, R2, T2 = 760, 30, 190, 30, 30
H2 = T2 + rowh * len(rows) + 30
xmin, xmax = 0.6, 2.8
xs2 = lambda v: L2 + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * (W2 - L2 - R2)
ss_ref = ssb['ago_out'][1]['prem']
g = [f'<svg viewBox="0 0 {W2} {H2}" role="img" aria-label="Prêmio dos prédios novos nos 3 primeiros meses e em ago–out 2026">']
for t in [0.6, 1.0, 1.4, 1.8, 2.2, 2.6]:
    x = xs2(t)
    g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T2-8}" y2="{H2-26}" class="{"axis0" if t == 1.0 else "grid"}"/>')
    g.append(f'<text x="{x:.1f}" y="{H2-8}" class="tick" text-anchor="middle">{prem(t,0)}</text>')
x = xs2(ss_ref)
g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{T2-8}" y2="{H2-26}" class="ref"/>')
g.append(f'<text x="{x+4:.1f}" y="{T2-14}" class="tick">same store ago–out/26: {prem(ss_ref,0)}</text>')
g.append(f'<text x="{xs2(1.0)-4:.1f}" y="{T2-14}" class="tick" text-anchor="end">= mercado</text>')
for j, r in enumerate(rows):
    y = T2 + j * rowh + rowh / 2
    a, b = r['m1_3'], r['l3']['prem']
    g.append(f'<text x="{L2-12}" y="{y+4:.1f}" class="rlab" text-anchor="end">{short(r["b"])} <tspan class="rsub">{CITY_SHORT.get(r["city"], "")} · {r["first"][5:7]}/{r["first"][2:4]}</tspan></text>')
    g.append(f'<line x1="{xs2(a):.1f}" x2="{xs2(b):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="bar {"up" if b >= a else "dn"}"/>')
    tip = f'{short(r["b"])}: 3 primeiros meses {prem(a)} → ago–out/26 {prem(b)}'
    g.append(f'<circle cx="{xs2(a):.1f}" cy="{y:.1f}" r="5" class="dot y25"><title>{tip}</title></circle>')
    g.append(f'<circle cx="{xs2(b):.1f}" cy="{y:.1f}" r="6" class="dot new"><title>{tip}</title></circle>')
    clip = ' ›' if b > xmax else ''
    g.append(f'<text x="{max(xs2(a), xs2(b)) + 10:.1f}" y="{y+4:.1f}" class="vlab">{prem(b,0)}{clip}</text>' if b >= a else
             f'<text x="{xs2(a) + 10:.1f}" y="{y+4:.1f}" class="vlab">{prem(b,0)}</text>')
g.append('</svg>')
chart2 = '\n'.join(g)

# ---------------------------------------------------------------- tabela: same store por período
PER = [('ytd', 'Jan–out'), ('t1', '1º tri'), ('t2', '2º tri'), ('t3', '3º tri'), ('out', 'Outubro'), ('nov', 'Nov 1–17')]
t = []
for k, lab in PER:
    a, b = ssb[k]
    t.append(f'''<tr class="{'em' if k == 'ytd' else ''}"><td>{lab}</td>
<td class="num r">{prem(a['prem'])}</td><td class="num r b">{prem(b['prem'])}</td>
<td class="num r {cls(b['prem']-a['prem'], .005)}">{dpp(a['prem'], b['prem'])}</td>
<td class="num r">{yoy(a['revpar'], b['revpar'])}</td><td class="num r">{yoy(a['mrevpar'], b['mrevpar'])}</td>
<td class="num r">{pct(a['occ'])} → {pct(b['occ'])}</td><td class="num r">{pct(a['mo'])} → {pct(b['mo'])}</td>
<td class="num r">{yoy(a['adr'], b['adr'])}</td><td class="num r">{yoy(a['madr'], b['madr'])}</td></tr>''')
tbl_periods = '\n'.join(t)

# ---------------------------------------------------------------- tabela: same store por prédio
t = []
for r in sorted(d['ss_buildings'], key=lambda r: -(r['y26']['prem'] - r['y25']['prem'])):
    a, b, a3, b3, an, bn = r['y25'], r['y26'], r['r25'], r['r26'], r['n25'], r['n26']
    t.append(f'''<tr><td><span class="bname">{short(r['b'])}</span> <span class="bsub">{long(r['b'])} · {CITY_SHORT.get(r['city'], '')}</span></td>
<td class="num r">{num(r['u26'], 0)}</td>
<td class="num r">{prem(a['prem'], 0)}</td><td class="num r b">{prem(b['prem'], 0)}</td>
<td class="num r {cls(b['prem']-a['prem'], .02)}">{dpp(a['prem'], b['prem'], 0)}</td>
<td class="num r">{prem(b3['prem'], 0)} <span class="{cls(b3['prem']-a3['prem'], .02)}">({dpp(a3['prem'], b3['prem'], 0)})</span></td>
<td class="num r">{prem(bn['prem'], 0)} <span class="{cls(bn['prem']-an['prem'], .02)}">({dpp(an['prem'], bn['prem'], 0)})</span></td>
<td class="num r">{yoy(a['revpar'], b['revpar'], 0)}</td><td class="num r">{yoy(a['mrevpar'], b['mrevpar'], 0)}</td>
<td class="num r">{pct(b['occ'])} / {pct(b['mo'])}</td><td class="num r">{num(b['adr'], 0)} / {num(b['madr'], 0)}</td></tr>''')
tbl_ss = '\n'.join(t)

# ---------------------------------------------------------------- tabela: prédios novos
t = []
for r in sorted([r for r in d['ramp'] if r['b'] not in d['excl_ramp']], key=lambda r: r['first']):
    l = r['l3']
    cell = lambda v: f'<td class="num r">{prem(v, 0)}</td>' if v is not None else '<td class="num r muted">–</td>'
    t.append(f'''<tr><td><span class="bname">{short(r['b'])}</span> <span class="bsub">{long(r['b'])} · {CITY_SHORT.get(r['city'], '')}</span></td>
<td class="num">{r['first'][8:10]}/{r['first'][5:7]}/{r['first'][2:4]}</td><td class="num r">{num(r['ytd26']['n']/304, 0) if r['ytd26'] else '–'}</td>
{cell(r['m1_3'])}{cell(r['m4_6'])}{cell(r['m7_12'])}
<td class="num r b">{prem(l['prem'], 0)}</td>
<td class="num r">{pct(l['occ'])} / {pct(l['mo'])}</td><td class="num r">{brl(l['adr'] or 0)} / {brl(l['madr'])}</td></tr>''')
tbl_new = '\n'.join(t)

# ---------------------------------------------------------------- mercado por cidade (heat)
MET = [('occ', 'Ocupação', 'pp'), ('mbp', 'Diária fechada', '%'), ('p50', 'Preço anunciado (p50)', '%'),
       ('rp', 'RevPAR', '%'), ('tal', 'Oferta no comp set', '%n')]


def heat(a, b, kind):
    if kind == 'pp':
        v = (b - a) * 100; txt = sg(v, 1); scale = v / 8
    else:
        v = (b / a - 1) * 100; txt = sg(v, 0) + '%'; scale = v / 20
    if kind == '%n':
        return f'<td class="num r hm neu">{txt}</td>'
    s = max(-1, min(1, scale))
    tone = 'pos' if s > 0 else 'neg'
    return f'<td class="num r hm" style="--a:{abs(s)*42:.0f}%" data-t="{tone}">{txt}</td>'


t = []
for c in ['São Paulo', 'Florianópolis', 'Balneário Camboriú', 'Total']:
    rows_c = d['mkt_city'][c]
    a_y, b_y = cy[c]
    for j, (k, lab, kind) in enumerate(MET):
        head = f'<th rowspan="{len(MET)}" class="cityh">{c if c != "Total" else "Portfólio"}</th>' if j == 0 else ''
        cells = ''.join(heat(r['a'][k], r['b'][k], kind) for r in rows_c)
        lvl = f'{pct(b_y[k])}' if k == 'occ' else (f'{brl(b_y[k])}' if k != 'tal' else '')
        t.append(f'<tr class="{"grp" if j == 0 else ""}">{head}<td class="mlab">{lab}</td>{cells}{heat(a_y[k], b_y[k], kind).replace("hm", "hm ytd")}<td class="num r muted">{lvl}</td></tr>')
tbl_city = '\n'.join(t)
city_cols = ''.join(f'<th class="r">{MLAB[r["m"]]}</th>' for r in d['mkt_city']['São Paulo'])

# ---------------------------------------------------------------- mercado por prédio
t = []
for cname in ['São Paulo', 'Florianópolis', 'Balneário Camboriú']:
    bs = [r for r in d['mkt_buildings'] if r['city'] == cname]
    bs.sort(key=lambda r: -(r['ytd']['b']['rp'] / r['ytd']['a']['rp']))
    t.append(f'<tr class="sub"><td colspan="10">{cname}</td></tr>')
    for r in bs:
        a, b = r['ytd']['a'], r['ytd']['b']
        f3 = (lambda g: f'<td class="num r {cls(g["b"]["rp"]/g["a"]["rp"]-1, .02)}">{yoy(g["a"]["rp"], g["b"]["rp"], 0)}</td>' if g else '<td class="num r muted">–</td>')
        nm = len(r['months'])
        base = 'jan–out' if nm == 10 else f'{MLAB[r["months"][0]]}–{MLAB[r["months"][-1]]}'
        t.append(f'''<tr><td><span class="bname">{short(r['b'])}</span> <span class="bsub">{long(r['b'])}{'' if r['ss'] else ' · novo'}</span></td>
<td class="num">{base}</td>
<td class="num r">{pct(a['occ'])} → {pct(b['occ'])} <span class="{cls(b['occ']-a['occ'], .02)}">({sg((b['occ']-a['occ'])*100, 1)})</span></td>
<td class="num r {cls(b['mbp']/a['mbp']-1, .02)}">{yoy(a['mbp'], b['mbp'], 0)}</td>
<td class="num r">{yoy(a['p50'], b['p50'], 0)}</td>
<td class="num r b {cls(b['rp']/a['rp']-1, .02)}">{yoy(a['rp'], b['rp'], 0)}</td>
<td class="num r muted">{yoy(a['tal'], b['tal'], 0)}</td>
{f3(r['l3'])}{f3(r['nov'])}<td class="num r">{brl(b['rp'])}</td></tr>''')
tbl_mkt = '\n'.join(t)

# ---------------------------------------------------------------- textos com números
sp_a, sp_b = cy['São Paulo']; fl_a, fl_b = cy['Florianópolis']; bc_a, bc_b = cy['Balneário Camboriú']
pvn = [r for r in d['ramp'] if r['b'].startswith('PVN')][0]['l3']
onz = [r for r in d['ramp'] if r['b'].startswith('ONZ')][0]

findings = [
    ('ss', f'<b>Same store estável no acumulado.</b> Nos 24 prédios que já operávamos antes de 2025, o prêmio de jan–out foi de {prem(ss_y25["prem"])} para {prem(ss_y26["prem"])} ({dpp(ss_y25["prem"], ss_y26["prem"])}). Nosso RevPAR andou {yoy(ss_y25["revpar"], ss_y26["revpar"])} e o do mercado desses prédios {yoy(ss_y25["mrevpar"], ss_y26["mrevpar"])}: acompanhamos o mercado, sem abrir nem perder distância. Melhoramos no 1º tri ({dpp(ssb["t1"][0]["prem"], ssb["t1"][1]["prem"])}) e ficamos estáveis no 2º e 3º tri.'),
    ('neg', f'<b>O prêmio same store caiu em outubro e no começo de novembro.</b> Outubro: {prem(ss_o25["prem"])} → {prem(ss_o26["prem"])}; nov 1–17: {prem(ss_n25["prem"])} → {prem(ss_n26["prem"])}. Em outubro o mercado subiu mais rápido que a gente (RevPAR do mercado {yoy(ss_o25["mrevpar"], ss_o26["mrevpar"])}, nosso {yoy(ss_o25["revpar"], ss_o26["revpar"])}). Em novembro nossa ocupação caiu de {pct(ss_n25["occ"])} para {pct(ss_n26["occ"])} com diária parada ({brl(ss_n25["adr"])} → {brl(ss_n26["adr"])}), enquanto a diária fechada do mercado subiu {yoy(ss_n25["madr"], ss_n26["madr"], 0)}. A queda é geral: {nov_down} dos 24 prédios perderam prêmio em nov 1–17.'),
    ('new', f'<b>Prédios novos rodam com prêmio maior e crescente.</b> Os prédios que entraram de fev/25 em diante tiveram prêmio de {prem(new26["prem"])} em jan–out/26, contra {prem(ss_y26["prem"])} do same store. {ramp_up} de {len(ramp_ok)} aumentaram o prêmio dos 3 primeiros meses para ago–out/26; os maiores saltos foram AGR, URB, PVF e PVP. Exceções: PVN segue abaixo do mercado ({prem(pvn["prem"], 0)} em ago–out; diária {brl(pvn["adr"])} contra {brl(pvn["madr"])} do mercado) e ONZ caiu de {prem(onz["m1_3"], 0)} para {prem(onz["l3"]["prem"], 0)}.'),
    ('all', f'<b>No portfólio inteiro o prêmio subiu</b> de {prem(all_y25["prem"])} para {prem(all_y26["prem"])} em jan–out, por mix: as unidades novas (prêmio maior) passaram a pesar {num(new26["n"]/all_y26["n"]*100, 0)}% das noites disponíveis.'),
    ('mkt', f'<b>O mercado ficou um pouco mais fraco em 2026.</b> Nos mesmos prédios, ponderado pelas nossas unidades, o RevPAR de mercado de jan–out andou {yoy(tot_a["rp"], tot_b["rp"])}: SP {yoy(sp_a["rp"], sp_b["rp"])}, Florianópolis {yoy(fl_a["rp"], fl_b["rp"])}, Balneário Camboriú {yoy(bc_a["rp"], bc_b["rp"])}. A diária fechada caiu ({yoy(tot_a["mbp"], tot_b["mbp"])}) enquanto o preço anunciado subiu ({yoy(tot_a["p50"], tot_b["p50"])}): o mercado anuncia mais caro e fecha mais barato. A oferta no comp set do Pricelabs cresceu {yoy(tot_a["tal"], tot_b["tal"], 0)}.'),
    ('sp', f'<b>SP virou em outubro.</b> RevPAR de mercado {yoy(sp_out["a"]["rp"], sp_out["b"]["rp"], 0)} em outubro (ocupação {sg((sp_out["b"]["occ"]-sp_out["a"]["occ"])*100)} p.p., preço anunciado {yoy(sp_out["a"]["p50"], sp_out["b"]["p50"], 0)}), depois de 9 meses entre −12% e +7%. É esse movimento que o nosso same store não acompanhou.'),
]
find_html = '\n'.join(f'<li><span class="dot {k}"></span><p>{txt}</p></li>' for k, txt in findings)

kpis = f'''
<div class="kpi"><span class="eyebrow">Same store · jan–out</span><span class="v">{prem(ss_y26['prem'])}</span><span class="s">2025: {prem(ss_y25['prem'])} · {dpp(ss_y25['prem'], ss_y26['prem'])}</span></div>
<div class="kpi warn"><span class="eyebrow">Same store · out e nov 1–17</span><span class="v">{prem(ss_o26['prem'], 0)} · {prem(ss_n26['prem'], 0)}</span><span class="s">2025: {prem(ss_o25['prem'], 0)} · {prem(ss_n25['prem'], 0)}</span></div>
<div class="kpi"><span class="eyebrow">Prédios novos · jan–out/26</span><span class="v">{prem(new26['prem'])}</span><span class="s">Entradas de fev/25 em diante · same store: {prem(ss_y26['prem'])}</span></div>
<div class="kpi"><span class="eyebrow">RevPAR do mercado · jan–out</span><span class="v">{yoy(tot_a['rp'], tot_b['rp'])}</span><span class="s">SP {yoy(sp_a['rp'], sp_b['rp'])} · FLN {yoy(fl_a['rp'], fl_b['rp'])} · BC {yoy(bc_a['rp'], bc_b['rp'])}</span></div>'''

page = open('template.html', encoding='utf-8').read()
for k, v in dict(KPIS=kpis, FINDINGS=find_html, CHART1=chart1, CHART2=chart2, TBL_PERIODS=tbl_periods, TBL_SS=tbl_ss,
                 TBL_NEW=tbl_new, TBL_CITY=tbl_city, CITY_COLS=city_cols, TBL_MKT=tbl_mkt,
                 SS_LIST=', '.join(short(b) for b in SS),
                 EXCL_LIST=', '.join(short(b) for b in d['excl_ramp'])).items():
    page = page.replace('{{' + k + '}}', v)
assert '{{' not in page, page[page.index('{{'):page.index('{{') + 40]
open('relatorio_premio_mercado.html', 'w', encoding='utf-8').write(page)
print('ok', len(page))
