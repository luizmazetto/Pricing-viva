"""Gera reviews_body.html (aba "Reviews × prêmio") a partir de reviews.json. Rode antes: python3 analysis_reviews.py"""
import json, html, math

d = json.load(open('reviews.json', encoding='utf-8'))
E, B = d['E'], d['bld']
MINUS = '−'
CITIES = ['São Paulo', 'Florianópolis', 'Balneário Camboriú']


def num(x, dec=1):
    s = f'{abs(x):,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return (MINUS if x < 0 and round(abs(x), dec) != 0 else '') + s
def sg(x, dec=1):
    if round(x, dec) == 0: return num(0, dec)
    return ('+' if x > 0 else MINUS) + num(abs(x), dec)
def pc(x, dec=1): return sg(x * 100, dec) + '%'
def prem(i, dec=0): return sg((i - 1) * 100, dec) + '%'
def st(x, dec=2): return num(x, dec) if x else '–'
def short(b): return html.escape(b.split(' - ', 1)[0])
def long(b): return html.escape(b.split(' - ', 1)[1].strip() if ' - ' in b else b)
def cls(v, thr=0.0): return 'pos' if v > thr else ('neg' if v < -thr else 'zero')
def ex(b, dx): return math.exp(b * dx) - 1

J = E['conjunto']; A0, K0 = E['ref_pesos']
def air_eff(share, y='lp', dx=0.1):      # +0,1 estrela Airbnb
    return ex(J[y]['ra_c']['b'] + J[y]['ra_x']['b'] * (share - A0), dx)
def bk_eff(share, y='lp', dx=0.1):       # +0,2 ponto Booking (= 0,1 "estrela")
    return ex(J[y]['rb_c']['b'] + J[y]['rb_x']['b'] * (share - K0), dx)
def clip(x, lo=0.15, hi=0.8): return min(max(x, lo), hi)

ea, em = E['entre_anuncios'], E['mesmo_anuncio']
ta, tb = E['tempo_airbnb'], E['tempo_booking']
cp = E['canal_proprio']

# ------------------------------------------------------------------ gráfico 1: faixas (desvio de nota vs desvio de prêmio)
bins = E['bins']
W, H, L, Rr, T, Bm = 760, 260, 60, 20, 20, 56
xs = lambda i: L + (i + 0.5) * (W - L - Rr) / len(bins)
vmax = max(abs(b['dev']) for b in bins); vmax = math.ceil(vmax * 50) / 50
ys = lambda v: T + (vmax - v) / (2 * vmax) * (H - T - Bm)
g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Prêmio relativo por faixa de nota exibida, comparado à média do prédio no mês">']
for t in [-vmax, -vmax / 2, 0, vmax / 2, vmax]:
    y = ys(t)
    g.append(f'<line x1="{L}" x2="{W-Rr}" y1="{y:.1f}" y2="{y:.1f}" class="{"axis0" if t == 0 else "grid"}"/>')
    g.append(f'<text x="{L-8}" y="{y+4:.1f}" class="tick" text-anchor="end">{pc(t, 0)}</text>')
bw = (W - L - Rr) / len(bins) * 0.56
for i, b in enumerate(bins):
    x = xs(i); y0 = ys(0); y1 = ys(b['dev'])
    top, h = min(y0, y1), max(abs(y1 - y0), 1)
    g.append(f'<rect x="{x-bw/2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" class="{"barp" if b["dev"] >= 0 else "barn"}"><title>Nota {b["lab"]} vs a média do prédio: prêmio {pc(b["dev"])} ({b["n"]} anúncios×mês)</title></rect>')
    g.append(f'<text x="{x:.1f}" y="{(y1-6 if b["dev"]>=0 else y1+14):.1f}" class="vlab" text-anchor="middle">{pc(b["dev"], 0)}</text>')
    g.append(f'<text x="{x:.1f}" y="{H-34}" class="tick" text-anchor="middle">{b["lab"]}</text>')
    g.append(f'<text x="{x:.1f}" y="{H-20}" class="tick" text-anchor="middle">n={b["n"]}</text>')
g.append(f'<text x="{(W+L)/2:.0f}" y="{H-4}" class="tick" text-anchor="middle">nota exibida no Airbnb menos a média dos anúncios do mesmo prédio no mês (estrelas)</text>')
g.append('</svg>')
chart_bins = '\n'.join(g)

# ------------------------------------------------------------------ gráfico 2: efeito de +0,1 estrela vs peso do canal
shares = [i / 100 for i in range(15, 81, 5)]
W2, H2, L2, R2, T2, B2 = 760, 270, 56, 120, 16, 40
ymax2 = math.ceil(max(air_eff(s) for s in shares) * 100) / 100 + 0.01
ymin2 = min(0, math.floor(min(bk_eff(s) for s in shares) * 100) / 100)
xs2 = lambda s: L2 + (s - 0.15) / 0.65 * (W2 - L2 - R2)
ys2 = lambda v: T2 + (ymax2 - v) / (ymax2 - ymin2) * (H2 - T2 - B2)
g = [f'<svg viewBox="0 0 {W2} {H2}" role="img" aria-label="Efeito no prêmio de +0,1 estrela por peso do canal na receita do anúncio">']
t = ymin2
while t <= ymax2 + 1e-9:
    y = ys2(t)
    g.append(f'<line x1="{L2}" x2="{W2-R2}" y1="{y:.1f}" y2="{y:.1f}" class="{"axis0" if abs(t) < 1e-9 else "grid"}"/>')
    g.append(f'<text x="{L2-8}" y="{y+4:.1f}" class="tick" text-anchor="end">{pc(t, 0)}</text>')
    t = round(t + 0.02, 4)
for s in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
    g.append(f'<text x="{xs2(s):.1f}" y="{H2-20}" class="tick" text-anchor="middle">{int(s*100)}%</text>')
g.append(f'<text x="{(W2-R2+L2)/2:.0f}" y="{H2-4}" class="tick" text-anchor="middle">peso do canal na receita do anúncio (2026)</text>')
for k, f, lab in (('y26', air_eff, 'Airbnb +0,1★'), ('new', bk_eff, 'Booking +0,2 pt')):
    pts = ' '.join(f'{xs2(s):.1f},{ys2(f(s)):.1f}' for s in shares)
    g.append(f'<polyline points="{pts}" class="ln {k}"/>')
    for s in shares:
        g.append(f'<circle cx="{xs2(s):.1f}" cy="{ys2(f(s)):.1f}" r="3.5" class="dot {k}"><title>{lab} com o canal em {int(s*100)}% da receita: prêmio {pc(f(s))}</title></circle>')
    g.append(f'<text x="{W2-R2+10}" y="{ys2(f(shares[-1]))+4:.1f}" class="dlab">{lab}</text>')
g.append('</svg>')
chart_share = '\n'.join(g)

# ------------------------------------------------------------------ tabelas de estimativas
def row_est(lab, how, x, per='+0,1★'):
    return f'<tr><td>{lab}</td><td class="small">{how}</td><td class="num r b">{pc(x["per01"])}</td><td class="num r muted">{pc(x["per01_lo"])} a {pc(x["per01_hi"])}</td></tr>'
est = ''.join([
    row_est('Airbnb · nota exibida', 'anúncios do mesmo prédio, no mesmo mês', ea),
    row_est('Airbnb · nota exibida', 'o mesmo anúncio ao longo do tempo', ta),
    row_est('Airbnb · nota dos últimos 12 meses', 'anúncios do mesmo prédio, no mesmo mês', E['entre_anuncios_12m']),
    row_est('Airbnb · nota dos últimos 12 meses', 'o mesmo anúncio ao longo do tempo', E['mesmo_anuncio_12m']),
    row_est('Booking · nota acumulada (+0,2 pt)', 'o mesmo anúncio ao longo do tempo', tb),
    row_est('Nota exibida média do prédio', 'o mesmo prédio ao longo do tempo', E['predio_tempo']),
])

def cell_eff(y, which):
    b = J[y]['ra_c' if which == 'a' else 'rb_c']
    return f'<td class="num r">{pc(ex(b["b"], .1))} <span class="muted">({pc(ex(b["lo"], .1), 1)} a {pc(ex(b["hi"], .1), 1)})</span></td>'
dim = ''.join(f'<tr><td>{lab}</td>{cell_eff(y, "a")}{cell_eff(y, "b")}</tr>' for y, lab in (('lp', 'Prêmio (RevPAR relativo)'), ('locc', 'Ocupação relativa ao mercado'), ('ladr', 'Diária relativa ao mercado')))
share_rows = ''.join(f'<tr><td class="num">{int(s*100)}%</td><td class="num r">{pc(air_eff(s))}</td><td class="num r">{pc(air_eff(s, "locc"))}</td><td class="num r">{pc(air_eff(s, "ladr"))}</td><td class="num r">{pc(bk_eff(s))}</td><td class="num r">{pc(bk_eff(s, "locc"))}</td><td class="num r">{pc(bk_eff(s, "ladr"))}</td></tr>' for s in (0.2, 0.35, 0.5, 0.65, 0.8))

SUBL = {'lo': 'Localização', 'ac': 'Precisão do anúncio', 'va': 'Custo-benefício', 'ci': 'Check-in', 'co': 'Comunicação', 'cl': 'Limpeza'}
subs = sorted(E['sub'], key=lambda k: -E['sub'][k] * E['sub_sd'][k])
sub_rows = ''.join(f'<tr><td>{SUBL[k]}</td><td class="num r">{pc(ex(E["sub"][k], .1))}</td><td class="num r">{num(E["sub_sd"][k], 2)}</td><td class="num r b">{pc(ex(E["sub"][k], E["sub_sd"][k]))}</td></tr>' for k in subs)

# ------------------------------------------------------------------ tabela por prédio
def bld_rows(city):
    out = []
    for b, x in sorted(B.items(), key=lambda kv: -(kv[1].get('air_share') or 0)):
        if x['city'] != city or not x.get('air_share') or x['n_total'] < 30: continue
        a, k = x['air_share'], x.get('bk_share') or 0
        r = [x['rev24'][0], x['rev25'][0], x['rev26'][0]]
        trend = ' → '.join(st(v) for v in r if v)
        de = (x['exib_oct26'] - x['exib_oct25']) if x['exib_oct26'] and x['exib_oct25'] else None
        bkt = f"{st(x['bk25'],1)} → {st(x['bk26'],1)}" if x['bk25'] else st(x['bk26'], 1)
        dp = (x['prem26'] - x['prem25']) if x['prem25'] and x['prem26'] else None
        sc = next((s for s in d['scen'] if s['b'] == b), None)
        eff_a = air_eff(clip(a)); eff_b = bk_eff(clip(k))
        proj = f"{st(sc['exib'])} → {st(sc['proj'])} <span class='{cls(sc['d'], .005)}'>({pc(math.exp((J['lp']['ra_c']['b'] + J['lp']['ra_x']['b'] * (clip(a) - A0)) * sc['d']) - 1)})</span>" if sc else '–'
        out.append(f'''<tr><td><span class="bname">{short(b)}</span><span class="bsub">{long(b)}{'' if x['ss'] else ' · novo'}</span></td>
<td class="num r">{pc(a,0).lstrip('+')} / {pc(k,0).lstrip('+')}</td>
<td class="num r">{trend}</td><td class="num r">{pc(x['rev26'][2],0).lstrip('+') if x['rev26'][2] else '–'}</td>
<td class="num r">{st(x['exib_oct25'])} → <b>{st(x['exib_oct26'])}</b> {f'<span class="{cls(de, .02)}">({sg(de, 2)})</span>' if de is not None else ''}</td>
<td class="num r">{bkt}</td>
<td class="num r">{prem(x['prem25']) if x['prem25'] else '–'} → <b>{prem(x['prem26']) if x['prem26'] else '–'}</b></td>
<td class="num r b">{pc(eff_a)}</td><td class="num r">{pc(eff_b)}</td><td class="num r">{proj}</td></tr>''')
    return ''.join(out)
bld_html = ''
for c in CITIES:
    rows = bld_rows(c)
    if rows: bld_html += f'<tr class="sub"><td colspan="10">{c}</td></tr>{rows}'

# ------------------------------------------------------------------ dispersão same store: Δ nota × Δ prêmio
pts = d['ss_pts']
W3, H3, L3, R3, T3, B3 = 620, 300, 74, 20, 14, 40
xr = max(abs(p['dr']) for p in pts) * 1.15; yr = max(abs(p['dp']) for p in pts) * 1.15
xs3 = lambda v: L3 + (v + xr) / (2 * xr) * (W3 - L3 - R3)
ys3 = lambda v: T3 + (yr - v) / (2 * yr) * (H3 - T3 - B3)
g = [f'<svg viewBox="0 0 {W3} {H3}" role="img" aria-label="Variação da nota dos últimos 12 meses e variação do prêmio, prédios same store">']
for v in (-0.2, -0.1, 0, 0.1, 0.2):
    if abs(v) > xr: continue
    g.append(f'<line x1="{xs3(v):.1f}" x2="{xs3(v):.1f}" y1="{T3}" y2="{H3-B3}" class="{"axis0" if v == 0 else "grid"}"/>')
    g.append(f'<text x="{xs3(v):.1f}" y="{H3-B3+16}" class="tick" text-anchor="middle">{sg(v, 1)}</text>')
for v in (-0.3, -0.2, -0.1, 0, 0.1, 0.2, 0.3):
    if abs(v) > yr: continue
    g.append(f'<line x1="{L3}" x2="{W3-R3}" y1="{ys3(v):.1f}" y2="{ys3(v):.1f}" class="{"axis0" if v == 0 else "grid"}"/>')
    g.append(f'<text x="{L3-8}" y="{ys3(v)+4:.1f}" class="tick" text-anchor="end">{sg(v*100, 0)} p.p.</text>')
for p in pts:
    k = 'y25' if p['city'] == 'São Paulo' else 'new'
    g.append(f'<circle cx="{xs3(p["dr"]):.1f}" cy="{ys3(p["dp"]):.1f}" r="{3+math.sqrt(p["u"])/1.6:.1f}" class="dot {k} sc"><title>{short(p["b"])}: nota 12m {sg(p["dr"], 2)}, prêmio {sg(p["dp"]*100, 0)} p.p.</title></circle>')
    if abs(p['dp']) > 0.05 or abs(p['dr']) > 0.08:
        g.append(f'<text x="{xs3(p["dr"])+8:.1f}" y="{ys3(p["dp"])-6:.1f}" class="tick">{short(p["b"]).split(" ")[0]}</text>')
g.append(f'<text x="{(W3+L3)/2:.0f}" y="{H3-6}" class="tick" text-anchor="middle">variação da nota Airbnb dos últimos 12 meses (out/26 vs out/25)</text>')
g.append('</svg>')
chart_ss = '\n'.join(g)

# ------------------------------------------------------------------ textos
air_avg = sum((x.get('air_share') or 0) * 1 for x in B.values() if x.get('air_share')) / len([x for x in B.values() if x.get('air_share')])
kpis = f'''
<div class="kpi"><span class="eyebrow">Airbnb · +0,1 estrela</span><span class="v">{pc(ea['per01'])}</span><span class="s">de prêmio entre anúncios do mesmo prédio · {pc(ta['per01'])} no mesmo anúncio ao longo do tempo</span></div>
<div class="kpi"><span class="eyebrow">Depende do peso do Airbnb</span><span class="v">{pc(air_eff(.25))} → {pc(air_eff(.7))}</span><span class="s">efeito de +0,1★ com o Airbnb em 25% → 70% da receita do anúncio</span></div>
<div class="kpi"><span class="eyebrow">Booking · +0,2 ponto (0–10)</span><span class="v">{pc(tb['per01'])}</span><span class="s">mesmo anúncio ao longo do tempo · entre anúncios {pc(bk_eff(K0))}, sem significância</span></div>
<div class="kpi"><span class="eyebrow">Em qual dimensão</span><span class="v">Ocupação</span><span class="s">~{num(J['locc']['ra_c']['b']/J['lp']['ra_c']['b']*100, 0)}% do efeito do Airbnb vem de vender mais noites; o resto, de diária</span></div>'''

find = [
    f'<b>A nota do Airbnb anda junto com o prêmio, e a relação é forte o suficiente para usar em cenário.</b> Dentro do mesmo prédio e mês, o anúncio com nota exibida 0,1 estrela acima da média do prédio tem prêmio {pc(ea["per01"])} maior (intervalo {pc(ea["per01_lo"])} a {pc(ea["per01_hi"])}). Acompanhando o mesmo anúncio ao longo do tempo, quando a nota exibida sobe 0,1 o prêmio sobe {pc(ta["per01"])}. O primeiro número inclui diferenças permanentes entre unidades (vista, andar, tamanho); o segundo é a estimativa mais conservadora.',
    f'<b>O que pesa é a nota exibida (acumulada), não a dos últimos meses.</b> A nota dos últimos 12 meses explica menos ({pc(E["mesmo_anuncio_12m"]["per01"])} por 0,1★ no mesmo anúncio), coerente com o hóspede vendo a média de todas as avaliações.',
    f'<b>O efeito escala com o volume do canal.</b> Estimando os dois canais juntos: com o Airbnb em 25% da receita do anúncio, +0,1★ vale {pc(air_eff(.25))} de prêmio; em 45%, {pc(air_eff(.45))}; em 70%, {pc(air_eff(.7))}. A nota do Airbnb puxa a receita do próprio Airbnb (+{num(cp["airbnb"]["b"]*10, 1)} p.p. de prêmio via Airbnb por 0,1★) e parte disso sai do Booking ({num(cp["cruz_air_bk"]*10, 1)} p.p.): é troca de canal, além de ganho líquido.',
    f'<b>No Booking a relação é mais fraca.</b> Entre anúncios do mesmo prédio ela não é estatisticamente diferente de zero; no mesmo anúncio ao longo do tempo, +0,2 ponto na nota (0–10) vale {pc(tb["per01"])} de prêmio. Onde o Booking pesa mais da receita, a nota dele passa a mexer na diária (interação significativa na diária).',
    f'<b>A dimensão é a ocupação.</b> Do efeito do Airbnb, cerca de {num(J["locc"]["ra_c"]["b"]/J["lp"]["ra_c"]["b"]*100, 0)}% vem de ocupação relativa ao mercado e o resto de diária. Entre as subnotas, as que mais acompanham o prêmio, por desvio-padrão, são {SUBL[subs[0]].lower()}, {SUBL[subs[1]].lower()} e {SUBL[subs[2]].lower()}; limpeza é a que menos diferencia (todo mundo tem nota alta e parecida).',
    f'<b>No nível do prédio, a nota quase não mudou e não explica a variação de prêmio de 2026.</b> A nota exibida média de cada prédio mexeu pouco entre out/25 e out/26 (desvio de ±0,05★), e a correlação entre variação de nota e variação de prêmio nos prédios same store é praticamente zero ({num(E["ss_corr_r12"], 2)}). O que moveu o prêmio em 2026 foi mercado e pricing (ver aba de prêmio); a nota é um efeito mais lento, que aparece entre unidades e ao longo de vários meses.',
]
find_html = ''.join(f'<li>{x}</li>' for x in find)

body = f'''
<section>
  <div class="sec-head"><span class="eyebrow">Reviews × prêmio</span><h2>Como a nota anda com o prêmio, por canal</h2>
  <p class="small">{num(d['meta']['n_reviews'], 0)} reviews do Airbnb e as notas do Booking dos prédios atuais, cruzados com o prêmio mensal de cada anúncio (nov/24 a out/26). A nota considerada em cada mês é a do fim do mês anterior, para não olhar o futuro.</p></div>
  <div class="kpis">{kpis}</div>
  <ul class="bul">{find_html}</ul>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">1 · A relação</span><h2>Nota acima da média do prédio, prêmio acima da média do prédio</h2>
  <p class="small">Cada barra junta anúncios × meses pela diferença entre a nota exibida no Airbnb e a média dos anúncios do mesmo prédio no mesmo mês. A altura é o prêmio relativo à média do prédio. Comparar dentro do prédio e do mês tira o efeito de mercado, localização e sazonalidade.</p></div>
  <div class="panel">{chart_bins}</div>
  <div class="tbl"><table class="t-est"><thead><tr><th>Nota</th><th>Comparação</th><th class="r">Prêmio por +0,1★</th><th class="r">Intervalo 90%</th></tr></thead><tbody>{est}</tbody></table></div>
  <p class="small">Intervalos por bootstrap sorteando prédios inteiros (200 repetições). Booking convertido para a mesma escala: +0,2 ponto na nota 0–10 = +0,1 estrela.</p>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">2 · Por canal e volume</span><h2>Quanto mais receita o canal traz, mais a nota dele pesa</h2>
  <p class="small">Modelo com as duas notas juntas (Airbnb e Booking) e interação com o peso de cada canal na receita do anúncio em 2026, comparando anúncios do mesmo prédio no mesmo mês ({num(E['conjunto_n'], 0)} anúncios × mês com pelo menos 10 reviews em cada canal).</p></div>
  <div class="panel"><div class="legend"><span><i class="c26"></i>Airbnb: +0,1 estrela</span><span><i class="cnew"></i>Booking: +0,2 ponto (0–10)</span></div>{chart_share}</div>
  <div class="tbl"><table class="t-share"><thead><tr><th>Peso do canal</th><th class="r">Airbnb +0,1★<br>prêmio</th><th class="r">ocupação</th><th class="r">diária</th><th class="r">Booking +0,2 pt<br>prêmio</th><th class="r">ocupação</th><th class="r">diária</th></tr></thead><tbody>{share_rows}</tbody></table></div>
  <h3>Em qual dimensão (no peso médio: Airbnb {int(A0*100)}%, Booking {int(K0*100)}%)</h3>
  <div class="tbl"><table class="t-dim"><thead><tr><th>Efeito de +0,1★</th><th class="r">Airbnb</th><th class="r">Booking (+0,2 pt)</th></tr></thead><tbody>{dim}</tbody></table></div>
  <h3>Qual subnota do Airbnb acompanha mais o prêmio</h3>
  <div class="tbl"><table class="t-sub2"><thead><tr><th>Subnota (acumulada)</th><th class="r">Prêmio por +0,1</th><th class="r">Desvio-padrão entre anúncios</th><th class="r">Prêmio por 1 desvio-padrão</th></tr></thead><tbody>{sub_rows}</tbody></table></div>
  <p class="small">Cada subnota testada sozinha, entre anúncios do mesmo prédio e mês. Como as subnotas andam juntas, não some os efeitos. "Por 1 desvio-padrão" compara subnotas que variam diferente: localização varia pouco dentro do prédio, limpeza varia pouco e quase não diferencia prêmio.</p>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">3 · Evolução por prédio</span><h2>Notas por prédio, peso de cada canal e sensibilidade do prêmio</h2>
  <p class="small">"Sensibilidade" aplica o modelo do item 2 ao peso de canal de cada prédio. "Cenário inercial" projeta a nota exibida de out/27 se os próximos 12 meses repetirem o volume e a nota dos últimos 12, e converte em prêmio.</p></div>
  <div class="tbl"><table class="t-bld"><thead><tr><th>Prédio</th><th class="r">Receita 26<br>Airbnb / Booking</th><th class="r">Nota Airbnb (reviews do ano)<br>2024 → 2025 → 2026</th><th class="r">5★<br>2026</th><th class="r">Nota exibida Airbnb<br>out/25 → out/26</th><th class="r">Booking (0–10)<br>2025 → 2026</th><th class="r">Prêmio jan–out<br>25 → 26</th><th class="r">+0,1★ Airbnb<br>→ prêmio</th><th class="r">+0,2 pt Booking<br>→ prêmio</th><th class="r">Cenário inercial out/27<br>nota exibida (prêmio)</th></tr></thead>
  <tbody>{bld_html}</tbody></table></div>
  <p class="small">Notas do ano = média dos reviews criados em jan–out (2024: ano inteiro). Nota exibida = média acumulada de todos os reviews do anúncio no Airbnb, ponderada pelas unidades do prédio.</p>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">4 · Prédio contra prédio</span><h2>Em 2026, nota e prêmio não andaram juntos no nível do prédio</h2>
  <p class="small">Prédios same store: variação da nota Airbnb dos últimos 12 meses (out/26 vs out/25) contra a variação do prêmio de jan–out. Tamanho do ponto = unidades. Azul = SP, verde = Florianópolis. Correlação: {num(E['ss_corr_r12'], 2)}.</p></div>
  <div class="panel">{chart_ss}</div>
  <p class="small">A nota média dos prédios oscila em décimos de estrela por ano, e um décimo vale de 1,7% a 3% de prêmio. A variação de prêmio entre 2025 e 2026 (de −20 a +20 p.p.) veio de mercado e pricing. Por isso a relação aparece com clareza entre anúncios e no mesmo anúncio ao longo do tempo, mas some na comparação ano contra ano por prédio.</p>
</section>

<section class="method">
  <div class="sec-head"><span class="eyebrow">Método</span><h2>Como foi calculado</h2></div>
  <ul>
    <li><b>Reviews:</b> mesma base do dashboard 70 (<code>Review</code> → <code>Reservation</code> → <code>Listing</code>), lida da réplica no BigQuery (<code>replicas.vivadb_review</code>, <code>vivadb_reservation</code>, <code>vivadb_listing</code>). Airbnb: <code>general</code> de 1 a 5. Booking: <code>general × 2</code> (0–10), como no card "General v2". Data = criação do review.</li>
    <li><b>Anúncio:</b> grupo master (<code>idCloneGroupMaster</code>), que é o anúncio onde a nota aparece; as notas das unidades do grupo são somadas. Nota exibida = média acumulada de todos os reviews até o fim do mês anterior; só anúncios com 10 ou mais reviews.</li>
    <li><b>Prêmio por anúncio:</b> mesma conta do dashboard 58 (RevPAR de hospedagem ÷ RevPAR do mercado), por grupo master e mês, de nov/24 a out/26, com pelo menos 20 noites disponíveis no mês.</li>
    <li><b>Canal:</b> participação de Airbnb e Booking na receita de hospedagem de 2026 (<code>partnerName</code> da reserva, a mesma informação da tabela <code>Calendar</code> e do card de GMV por canal).</li>
    <li><b>Estimativas:</b> regressão do log do prêmio na nota, com efeitos fixos de prédio × mês ("entre anúncios") e, adicionalmente, de anúncio ("mesmo anúncio ao longo do tempo"), ponderada pelas noites disponíveis. Ocupação e diária relativas ao mercado decompõem o prêmio (log prêmio = log ocupação relativa + log diária relativa).</li>
    <li><b>Limites:</b> é correlação, não experimento. Comparar dentro do prédio e do mês tira mercado e sazonalidade; o efeito fixo de anúncio tira diferenças permanentes entre unidades. Mesmo assim, uma melhora operacional pode subir nota e vendas ao mesmo tempo, e preço alto pode baixar a nota de custo-benefício. Use os números como ordem de grandeza para cenários: 1,7% (conservador) a 3% (alto) de prêmio por 0,1★ no Airbnb, escalando com o peso do canal.</li>
  </ul>
</section>
'''
open('reviews_body.html', 'w', encoding='utf-8').write(body)
print('ok', len(body))
