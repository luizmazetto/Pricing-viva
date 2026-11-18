"""Gera reviews_body.html (aba "Reviews × prêmio"), com foco no nível prédio.
Rode antes: python3 analysis_reviews.py && python3 analysis_robustez.py && python3 analysis_tempo.py"""
import json, html, math

RV = json.load(open('reviews.json', encoding='utf-8'))
RB = json.load(open('robustez.json', encoding='utf-8'))
TP = json.load(open('tempo.json', encoding='utf-8'))
B = RV['bld']
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
def ci(e): return f'{pc(e["p01_lo"])} a {pc(e["p01_hi"])}'
def sig(e): return e['p01_lo'] > 0 or e['p01_hi'] < 0

PA = {r['lab']: r for r in TP['predio_airbnb']}
PK = {r['lab'].replace('BK ', ''): r for r in TP['predio_booking']}
acc, w12 = PA['Acumulada (nota exibida)'], PA['Últimos 12 meses']
w6, w3 = PA['Últimos 6 meses'], PA['Últimos 3 meses']
plac = PA['Próximos 3 meses (placebo)']
SPL = TP['split_air']; hi_g, lo_g = SPL['Airbnb ≥ 50% da receita'], SPL['Airbnb < 50% da receita']
hi12 = [r for r in hi_g['res'] if r['lab'] == 'Últimos 12 meses'][0]; lo12 = [r for r in lo_g['res'] if r['lab'] == 'Últimos 12 meses'][0]
hiac = [r for r in hi_g['res'] if r['lab'].startswith('Acum')][0]; loac = [r for r in lo_g['res'] if r['lab'].startswith('Acum')][0]
LAG = {r['k']: r for r in TP['defasagem']}
ISO = RB['isolamento']; JL = {r['lab']: r for r in RB['janelas']}
mat_ = TP['predio_maduro'][0]; nov_ = TP['predio_novo'][0]

# ------------------------------------------------------------------ tabela de janelas (nível prédio, Airbnb e Booking)
ORDER = ['Acumulada (nota exibida)', 'Meia-vida 24 meses', 'Últimos 24 meses', 'Meia-vida 12 meses', 'Últimos 12 meses',
         'Meia-vida 6 meses', 'Últimos 6 meses', 'Meia-vida 3 meses', 'Últimos 3 meses', 'Próximos 3 meses (placebo)']
def cell(e):
    return f'<td class="num r {"b" if sig(e) else "muted"}">{pc(e["p01"])}</td><td class="num r muted">{ci(e)}</td>'
win_rows = ''
for l in ORDER:
    a, k = PA[l], PK.get(l)
    win_rows += f'<tr class="{"em" if l.startswith("Acum") else ""}"><td>{l}</td>{cell(a["est"])}{cell(k["est"]) if k else "<td></td><td></td>"}</tr>'

# ------------------------------------------------------------------ gráfico 1: janelas (barras horizontais Airbnb, nível prédio)
W, rowh, L, Rr, T = 760, 28, 230, 70, 24
H = T + rowh * len(ORDER) + 30
lo_x, hi_x = -0.04, 0.09
xs = lambda v: L + (min(max(v, lo_x), hi_x) - lo_x) / (hi_x - lo_x) * (W - L - Rr)
g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Prêmio por +0,1 estrela no Airbnb, por janela de reviews, nível prédio">']
for t in (-0.04, -0.02, 0, 0.02, 0.04, 0.06, 0.08):
    g.append(f'<line x1="{xs(t):.1f}" x2="{xs(t):.1f}" y1="{T-6}" y2="{H-26}" class="{"axis0" if t == 0 else "grid"}"/>')
    g.append(f'<text x="{xs(t):.1f}" y="{H-8}" class="tick" text-anchor="middle">{pc(t, 0)}</text>')
for j, l in enumerate(ORDER):
    e = PA[l]['est']; y = T + j * rowh + rowh / 2
    k = 'y26' if sig(e) else 'y25'
    g.append(f'<text x="{L-12}" y="{y+4:.1f}" class="rlab" text-anchor="end">{l}</text>')
    g.append(f'<line x1="{xs(e["p01_lo"]):.1f}" x2="{xs(e["p01_hi"]):.1f}" y1="{y:.1f}" y2="{y:.1f}" class="cil"/>')
    g.append(f'<circle cx="{xs(e["p01"]):.1f}" cy="{y:.1f}" r="5.5" class="dot {k}"><title>{l}: {pc(e["p01"])} por +0,1★ (90%: {ci(e)})</title></circle>')
    g.append(f'<text x="{xs(e["p01_hi"])+8:.1f}" y="{y+4:.1f}" class="vlab">{pc(e["p01"])}</text>')
g.append('</svg>')
chart_win = '\n'.join(g)

# ------------------------------------------------------------------ gráfico 2: dentro do prédio, nota 12m vs prêmio (faixas)
bins = TP['bins_predio']
W2, H2, L2, R2, T2, B2 = 760, 270, 60, 20, 18, 64
vmax = max(0.06, max(abs(b['y']) for b in bins)); vmax = math.ceil(vmax * 50) / 50
xs2 = lambda i: L2 + (i + .5) * (W2 - L2 - R2) / len(bins)
ys2 = lambda v: T2 + (vmax - v) / (2 * vmax) * (H2 - T2 - B2)
g = [f'<svg viewBox="0 0 {W2} {H2}" role="img" aria-label="Desvio da nota do prédio em relação à própria média e desvio do prêmio">']
for t in (-vmax, -vmax / 2, 0, vmax / 2, vmax):
    g.append(f'<line x1="{L2}" x2="{W2-R2}" y1="{ys2(t):.1f}" y2="{ys2(t):.1f}" class="{"axis0" if t == 0 else "grid"}"/>')
    g.append(f'<text x="{L2-8}" y="{ys2(t)+4:.1f}" class="tick" text-anchor="end">{pc(t, 0)}</text>')
bw = (W2 - L2 - R2) / len(bins) * .55
for i, b in enumerate(bins):
    y0, y1 = ys2(0), ys2(b['y']); top = min(y0, y1); h = max(abs(y1 - y0), 1)
    g.append(f'<rect x="{xs2(i)-bw/2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="3" class="{"barp" if b["y"] >= 0 else "barn"}"><title>Nota 12m {sg(b["x"], 2)}★ vs a média do próprio prédio: prêmio {pc(b["y"])} ({b["n"]} prédio×mês)</title></rect>')
    g.append(f'<text x="{xs2(i):.1f}" y="{(y1-6 if b["y"]>=0 else y1+14):.1f}" class="vlab" text-anchor="middle">{pc(b["y"], 1)}</text>')
    g.append(f'<text x="{xs2(i):.1f}" y="{H2-28}" class="tick" text-anchor="middle">{sg(b["x"], 2)}★</text>')
g.append(f'<text x="{(W2+L2)/2:.0f}" y="{H2-8}" class="tick" text-anchor="middle">nota Airbnb dos últimos 12 meses do prédio menos a média do próprio prédio (descontado o mês)</text>')
g.append('</svg>')
chart_bins = '\n'.join(g)

lag_rows = ''.join(f'<tr><td>{k} {"mês" if k == 1 else "meses"} antes</td><td class="num r {"b" if sig(r["est"]) else "muted"}">{pc(r["est"]["p01"])}</td><td class="num r muted">{ci(r["est"])}</td></tr>' for k, r in LAG.items())
dim_rows = f'''<tr><td>Prêmio (RevPAR relativo)</td><td class="num r b">{pc(acc["est"]["p01"])}</td><td class="num r muted">{ci(acc["est"])}</td></tr>
<tr><td>Diária relativa ao mercado</td><td class="num r b">{pc(TP["dim_ladr"]["p01"])}</td><td class="num r muted">{ci(TP["dim_ladr"])}</td></tr>
<tr><td>Ocupação relativa ao mercado</td><td class="num r muted">{pc(TP["dim_locc"]["p01"])}</td><td class="num r muted">{ci(TP["dim_locc"])}</td></tr>'''

def split_row(lab, gg):
    rs = {r['lab']: r for r in gg['res']}; ks = {r['lab'].replace('BK ', ''): r for r in gg['bk']}
    c = lambda e: f'<td class="num r {"b" if sig(e) else "muted"}">{pc(e["p01"])} <span class="muted">({ci(e)})</span></td>'
    return f'<tr><td>{lab} <span class="bsub">{gg["nb"]} prédios</span></td>{c(rs["Acumulada (nota exibida)"]["est"])}{c(rs["Últimos 12 meses"]["est"])}{c(rs["Últimos 6 meses"]["est"])}{c(ks["Acumulada (nota exibida)"]["est"])}{c(ks["Últimos 12 meses"]["est"])}</tr>'
split_rows = split_row('Airbnb ≥ 50% da receita', hi_g) + split_row('Airbnb < 50% da receita', lo_g)

# nível anúncio (apoio)
def lrow(lab, e, n, note=''):
    return f'<tr><td>{lab}{note}</td><td class="num r">{num(n, 0)}</td><td class="num r {"b" if sig(e) else "muted"}">{pc(e["p01"])}</td><td class="num r muted">{ci(e)}</td></tr>'
list_rows = (lrow('Todos os anúncios · nota exibida', ISO['4_mesmo_anuncio']['est'], ISO['4_mesmo_anuncio']['n']) +
             lrow('Anúncios no 1º ano de reviews', ISO['5_mesmo_anuncio_jovem']['est'], ISO['5_mesmo_anuncio_jovem']['n']) +
             lrow('Anúncios com 12+ meses de reviews', ISO['6_mesmo_anuncio_maduro']['est'], ISO['6_mesmo_anuncio_maduro']['n']) +
             ''.join(lrow(f'Janela: {l}', JL[l]['mesmo'], JL[l]['n']) for l in ('Últimos 24 meses', 'Últimos 12 meses', 'Últimos 6 meses', 'Últimos 3 meses', 'Próximos 3 meses (placebo)')))

# ------------------------------------------------------------------ tabela por prédio
EH, EL = hi12['est']['b'], lo12['est']['b']           # elasticidade por grupo de peso do Airbnb (janela 12m)
def bld_rows(city):
    out = []
    for b, x in sorted(B.items(), key=lambda kv: -(kv[1].get('air_share') or 0)):
        if x['city'] != city or not x.get('air_share') or x['n_total'] < 30: continue
        a, k = x['air_share'], x.get('bk_share') or 0
        el = EH if a >= 0.5 else EL
        r = [x['rev24'][0], x['rev25'][0], x['rev26'][0]]
        trend = ' → '.join(st(v) for v in r if v)
        de = (x['exib_oct26'] - x['exib_oct25']) if x['exib_oct26'] and x['exib_oct25'] else None
        dr12 = (x['r12_oct26'] - x['r12_oct25']) if x['r12_oct26'] and x['r12_oct25'] else None
        bkt = f"{st(x['bk25'],1)} → {st(x['bk26'],1)}" if x['bk25'] else st(x['bk26'], 1)
        sc = next((s for s in RV['scen'] if s['b'] == b), None)
        proj = f"{st(sc['exib'])} → {st(sc['proj'])} <span class='{cls(sc['d'], .005)}'>({pc(math.exp(el * sc['d']) - 1)})</span>" if sc else '–'
        out.append(f'''<tr><td><span class="bname">{short(b)}</span><span class="bsub">{long(b)}{'' if x['ss'] else ' · novo'}</span></td>
<td class="num r">{pc(a,0).lstrip('+')} / {pc(k,0).lstrip('+')}</td>
<td class="num r">{trend}</td><td class="num r">{st(x['exib_oct25'])} → <b>{st(x['exib_oct26'])}</b> {f'<span class="{cls(de, .02)}">({sg(de, 2)})</span>' if de is not None else ''}</td>
<td class="num r">{f'<span class="{cls(dr12, .02)}">{sg(dr12, 2)}</span>' if dr12 is not None else '–'}</td>
<td class="num r">{bkt}</td>
<td class="num r">{prem(x['prem25']) if x['prem25'] else '–'} → <b>{prem(x['prem26']) if x['prem26'] else '–'}</b></td>
<td class="num r b">{pc(math.exp(el * .1) - 1)}</td><td class="num r">{proj}</td></tr>''')
    return ''.join(out)
bld_html = ''
for c in CITIES:
    rows = bld_rows(c)
    if rows: bld_html += f'<tr class="sub"><td colspan="9">{c}</td></tr>{rows}'

# ------------------------------------------------------------------ textos
kpis = f'''
<div class="kpi"><span class="eyebrow">Airbnb · prédio ao longo do tempo</span><span class="v">{pc(acc['est']['p01'])}</span><span class="s">de prêmio por +0,1★ na nota exibida (90%: {ci(acc['est'])})</span></div>
<div class="kpi"><span class="eyebrow">Depende do peso do Airbnb</span><span class="v">{pc(hi12['est']['p01'])} · {pc(lo12['est']['p01'])}</span><span class="s">por +0,1★ (nota 12m) em prédios com Airbnb ≥ 50% · &lt; 50% da receita</span></div>
<div class="kpi"><span class="eyebrow">Booking · nota do prédio</span><span class="v">≈ 0</span><span class="s">nenhuma janela mostra relação com o prêmio ({pc(PK['Acumulada (nota exibida)']['est']['p01'])} na acumulada)</span></div>
<div class="kpi"><span class="eyebrow">Janela e dimensão</span><span class="v">12–24 meses</span><span class="s">reviews recentes (3–6 meses) não pesam mais; o efeito aparece na diária, não na ocupação</span></div>'''

find = [
    f'<b>No nível do prédio, a nota do Airbnb anda junto com o prêmio.</b> Comparando cada prédio com ele mesmo ao longo do tempo (o que já tira localização, tamanho e padrão das unidades) e descontando o mês, +0,1 estrela na nota exibida do prédio vem com {pc(acc["est"]["p01"])} de prêmio (intervalo de 90%: {ci(acc["est"])}). Com a nota dos últimos 12 meses o resultado é parecido ({pc(w12["est"]["p01"])}, {ci(w12["est"])}).',
    f'<b>Reviews mais recentes não pesam mais.</b> Quanto mais longa a memória da nota, mais ela acompanha o prêmio: meia-vida de 3 meses {pc(PA["Meia-vida 3 meses"]["est"]["p01"])}, 6 meses {pc(PA["Meia-vida 6 meses"]["est"]["p01"])}, 12 meses {pc(PA["Meia-vida 12 meses"]["est"]["p01"])}, 24 meses {pc(PA["Meia-vida 24 meses"]["est"]["p01"])}. A nota só dos últimos 6 ou 3 meses não tem relação detectável ({pc(w6["est"]["p01"])} e {pc(w3["est"]["p01"])}). No nível anúncio, somar a nota dos últimos 6 meses à nota exibida não acrescenta nada. O que conta é a nota que o hóspede vê, que é a média de todo o histórico.',
    f'<b>O efeito aparece rápido.</b> A nota de 1 a 3 meses antes acompanha o prêmio ({pc(LAG[1]["est"]["p01"])} e {pc(LAG[3]["est"]["p01"])}); a de 6 meses antes já perde força ({pc(LAG[6]["est"]["p01"])}) e a de 9–12 meses não aparece. Teste placebo: os reviews dos <i>próximos</i> 3 meses não acompanham o prêmio de hoje ({pc(plac["est"]["p01"])}), o que é coerente com a nota puxando o prêmio, e não o contrário.',
    f'<b>Depende do peso do Airbnb no prédio.</b> Nos {hi_g["nb"]} prédios em que o Airbnb é 50% ou mais da receita, +0,1★ (nota 12m) vale {pc(hi12["est"]["p01"])} de prêmio ({ci(hi12["est"])}). Nos {lo_g["nb"]} prédios em que o Airbnb pesa menos, a relação some ({pc(lo12["est"]["p01"])}).',
    f'<b>A nota do Booking (que é do prédio) não mostra relação com o prêmio</b> em nenhuma janela, nem nos prédios mais dependentes de Booking: os efeitos ficam entre {pc(min(r["est"]["p01"] for r in TP["predio_booking"]))} e {pc(max(r["est"]["p01"] for r in TP["predio_booking"]))} por +0,2 ponto, sem significância.',
    f'<b>A dimensão é a diária.</b> Quando a nota do prédio sobe, o prêmio sobe pela diária relativa ao mercado ({pc(TP["dim_ladr"]["p01"])} por 0,1★); a ocupação relativa fica igual ({pc(TP["dim_locc"]["p01"])}). Na prática, prédio com nota melhor sustenta preço mais alto com a mesma ocupação.',
    f'<b>Na prática, a nota mexe pouco no prêmio dos prédios maduros.</b> Depois de 12 meses de reviews, a nota exibida de um prédio quase não se move (desvio de {num(mat_["sd"], 3)}★ em relação à própria tendência), e nesses prédios o efeito não se separa do ruído. A relação se vê nos prédios em formação (1º ano) e nos que dependem mais de Airbnb. Por isso a nota não explica a variação de prêmio de 2026 (aba de prêmio): ela é um fator de nível, que se forma no começo e muda devagar.',
]
find_html = ''.join(f'<li>{x}</li>' for x in find)

body = f'''
<section>
  <div class="sec-head"><span class="eyebrow">Reviews × prêmio</span><h2>Como a nota do prédio anda com o prêmio, por canal e por janela</h2>
  <p class="small">Cada prédio comparado com ele mesmo ao longo do tempo (nov/24 a out/26), descontando o que aconteceu no mês para todos. Assim, características das unidades (tamanho, andar, vista, padrão) ficam fixas e saem da conta. Airbnb: nota do prédio = reviews de todos os anúncios. Booking: a nota já é do prédio. A nota de cada mês é a do fim do mês anterior.</p></div>
  <div class="kpis">{kpis}</div>
  <ul class="bul">{find_html}</ul>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">1 · Janelas</span><h2>Memória longa: a nota de 12 a 24 meses é a que acompanha o prêmio</h2>
  <p class="small">Efeito no prêmio do prédio de +0,1★ no Airbnb e de +0,2 ponto (0–10) no Booking, para cada forma de medir a nota. "Meia-vida" dá mais peso aos reviews recentes: com meia-vida de 3 meses, um review de 3 meses atrás vale metade de um de hoje. Ponto laranja = diferente de zero com 90% de confiança.</p></div>
  <div class="panel"><div class="legend"><span><i class="dt c26"></i>significativo</span><span><i class="dt c25"></i>não significativo</span><span>linha = intervalo de 90%</span></div>{chart_win}</div>
  <div class="tbl"><table class="t-win"><thead><tr><th>Nota</th><th class="r">Airbnb +0,1★</th><th class="r">Intervalo 90%</th><th class="r">Booking +0,2 pt</th><th class="r">Intervalo 90%</th></tr></thead><tbody>{win_rows}</tbody></table></div>
  <p class="small">{TP['n_predio_mes']} prédio × mês, {TP['n_predios']} prédios com pelo menos 30 reviews no Airbnb. Intervalos por bootstrap sorteando prédios inteiros (300 repetições).</p>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">2 · Como andam juntos</span><h2>Quando a nota do prédio fica acima da própria média, o prêmio acompanha, com ruído</h2>
  <p class="small">Prédio × mês agrupados pelo quanto a nota Airbnb dos últimos 12 meses ficou acima ou abaixo da média do próprio prédio. A altura é o prêmio em relação à média do prédio. As variações de nota dentro de um prédio são pequenas (décimos de estrela), por isso o sinal é fraco mês a mês.</p></div>
  <div class="panel">{chart_bins}</div>
  <div class="duo">
    <div class="col"><h3>Quanto tempo leva (nota exibida de k meses antes)</h3><div class="tbl"><table class="t-lag"><thead><tr><th>Nota de</th><th class="r">Prêmio por +0,1★</th><th class="r">Intervalo 90%</th></tr></thead><tbody>{lag_rows}</tbody></table></div></div>
    <div class="col"><h3>Em qual dimensão (Airbnb, nota exibida)</h3><div class="tbl"><table class="t-lag"><thead><tr><th>Efeito de +0,1★ em</th><th class="r">Efeito</th><th class="r">Intervalo 90%</th></tr></thead><tbody>{dim_rows}</tbody></table></div></div>
  </div>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">3 · Por canal</span><h2>Só pesa onde o Airbnb é grande; Booking não aparece</h2>
  <p class="small">Prédios separados pela participação do Airbnb na receita de hospedagem em 2026. Airbnb por +0,1★; Booking por +0,2 ponto (0–10).</p></div>
  <div class="tbl"><table class="t-split"><thead><tr><th>Grupo</th><th class="r">Airbnb · nota exibida</th><th class="r">Airbnb · 12 meses</th><th class="r">Airbnb · 6 meses</th><th class="r">Booking · acumulada</th><th class="r">Booking · 12 meses</th></tr></thead><tbody>{split_rows}</tbody></table></div>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">4 · Apoio: nível anúncio (Airbnb)</span><h2>Cada anúncio contra ele mesmo confirma o padrão</h2>
  <p class="small">A nota do Airbnb é por anúncio. Comparando cada anúncio com ele mesmo ao longo do tempo (descontado o prédio no mês), o resultado repete o do prédio: memória longa, efeito concentrado no primeiro ano de reviews e nenhum sinal nos reviews futuros.</p></div>
  <div class="tbl"><table class="t-lst"><thead><tr><th>Mesmo anúncio ao longo do tempo</th><th class="r">Anúncio × mês</th><th class="r">Prêmio por +0,1★</th><th class="r">Intervalo 90%</th></tr></thead><tbody>{list_rows}</tbody></table></div>
</section>

<section>
  <div class="sec-head"><span class="eyebrow">5 · Por prédio</span><h2>Notas, peso de cada canal e cenário</h2>
  <p class="small">"+0,1★ → prêmio" usa o efeito do grupo do prédio (Airbnb ≥ 50%: {pc(hi12['est']['p01'])}; &lt; 50%: {pc(lo12['est']['p01'])}). "Cenário inercial" projeta a nota exibida de out/27 se os próximos 12 meses repetirem volume e nota dos últimos 12 e converte em prêmio com o mesmo efeito. Booking sem efeito no prêmio.</p></div>
  <div class="tbl"><table class="t-bld"><thead><tr><th>Prédio</th><th class="r">Receita 26<br>Airbnb / Booking</th><th class="r">Nota Airbnb (reviews do ano)<br>2024 → 2025 → 2026</th><th class="r">Nota exibida Airbnb<br>out/25 → out/26</th><th class="r">Nota 12m<br>Δ out/26 vs out/25</th><th class="r">Booking (0–10)<br>2025 → 2026</th><th class="r">Prêmio jan–out<br>25 → 26</th><th class="r">+0,1★ Airbnb<br>→ prêmio</th><th class="r">Cenário inercial out/27<br>nota exibida (prêmio)</th></tr></thead>
  <tbody>{bld_html}</tbody></table></div>
</section>

<section class="method">
  <div class="sec-head"><span class="eyebrow">Método</span><h2>Como foi calculado</h2></div>
  <ul>
    <li><b>Reviews:</b> mesma base do dashboard 70 (<code>Review</code> → <code>Reservation</code> → <code>Listing</code>), pela réplica no BigQuery. Airbnb: <code>general</code> 1–5. Booking: <code>general × 2</code> (0–10). Data = criação do review.</li>
    <li><b>Nota do prédio:</b> Airbnb = média dos reviews de todos os anúncios do prédio na janela; "nota exibida" = média de todo o histórico até o fim do mês anterior. Booking = média dos reviews do prédio (a nota no Booking é do prédio).</li>
    <li><b>Prêmio do prédio:</b> mesma conta do dashboard 58 (RevPAR de hospedagem ÷ RevPAR do mercado), por mês, com pelo menos 150 noites disponíveis.</li>
    <li><b>Estimativa:</b> regressão do log do prêmio na nota com efeito fixo de prédio (cada prédio contra ele mesmo) e de mês (tira o que afeta todos no mês), ponderada pelas noites disponíveis. Intervalos de 90% por bootstrap sorteando prédios.</li>
    <li><b>Canal:</b> participação do Airbnb e do Booking na receita de hospedagem de 2026 (<code>partnerName</code> da reserva, a mesma informação da <code>Calendar</code>).</li>
    <li><b>Limites:</b> com {TP['n_predios']} prédios e notas que mudam pouco, os intervalos são largos. Use como ordem de grandeza: ~+3% a +5% de prêmio por +0,1★ no Airbnb em prédios onde o Airbnb é metade ou mais da receita, perto de zero nos demais, e zero para a nota do Booking. É correlação ao longo do tempo: uma melhora operacional pode subir nota e preço juntos.</li>
  </ul>
</section>
'''
open('reviews_body.html', 'w', encoding='utf-8').write(body)
print('ok', len(body))
