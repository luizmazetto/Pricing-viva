"""Seção "Fórmula e calculadora" da aba de reviews (usada por build_reviews.py). Lê formula.json."""
import json, html, math

F = json.load(open('formula.json', encoding='utf-8'))
MINUS = '−'
PA, PB_ = F['prop']['coef']                 # proporcional: por (peso × estrela) e por (peso × ponto Booking)
PDR = F['prop']['draws']
a0, a1, b0, b1 = F['final']['coef']         # alternativa com limiar
LDR = F['final']['draws']


def num(x, dec=1):
    s = f'{abs(x):,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return (MINUS if x < 0 and round(abs(x), dec) != 0 else '') + s
def sg(x, dec=1):
    if round(x, dec) == 0: return num(0, dec)
    return ('+' if x > 0 else MINUS) + num(abs(x), dec)
def pctl(v, q): v = sorted(v); return v[min(len(v) - 1, int(q * len(v)))]

def eff_prop(air, dra, coef=(PA, PB_), bk=0, drb=0, use_bk=False):
    return math.exp(coef[0] * air * dra + (coef[1] * bk * drb if use_bk else 0)) - 1
def eff_lim(air, dra, coef=(a0, a1, b0, b1)):
    return math.exp(max(0.0, coef[0] + coef[1] * air) * dra) - 1


def sens_table(base=0.15):
    shares = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    deltas = [-0.2, -0.1, 0.1, 0.2]
    head = ''.join(f'<th class="r">{sg(d, 1)}★</th>' for d in deltas)
    rows = ''
    for s in shares:
        cells = ''
        for d in deltas:
            e = eff_prop(s, d); lo = pctl([eff_prop(s, d, c) for c in PDR], .05); hi = pctl([eff_prop(s, d, c) for c in PDR], .95)
            cells += f'<td class="num r">{sg(e*100)}% <span class="muted">({sg((1+base)*e*100)} p.p.)</span><span class="ci">{sg(lo*100)} a {sg(hi*100)}%</span></td>'
        rows += f'<tr><td class="num">{int(s*100)}%</td><td class="num r">{num(PA * s, 2)}</td>{cells}</tr>'
    return f'''<div class="tbl"><table class="t-sens"><thead><tr><th>Airbnb no GMV</th><th class="r">Coeficiente<br>(por estrela)</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'''


def calculator():
    pre = [dict(b=p['b'].split(' - ', 1)[0], nome=p['b'].split(' - ', 1)[1].strip(), air=round(p['air'] * 100), bk=round((p['bk'] or 0) * 100),
                prem=round((p['prem'] - 1) * 100, 1) if p.get('prem') else 15.0,
                ra=round(p['ra12'], 2) if p.get('ra12') else 4.7, rb=round(p['rb26'], 1) if p.get('rb26') else 8.5) for p in F['predios']]
    opts = '<option value="">Personalizado</option>' + ''.join(f'<option value="{i}">{html.escape(p["b"])} · {html.escape(p["nome"])}</option>' for i, p in enumerate(pre))
    data = json.dumps(dict(p=[PA, PB_], pd=PDR, l=[a0, a1], ld=[c[:2] for c in LDR], b=pre), separators=(',', ':'))
    return f'''
<div class="calc panel">
  <div class="calc-grid">
    <label class="fld wide" for="cf-predio"><span>Prédio (preenche os campos com os dados atuais)</span><select id="cf-predio">{opts}</select></label>
    <label class="fld" for="cf-air"><span>Airbnb no GMV (%)</span><input id="cf-air" type="number" min="0" max="100" step="1" value="50"></label>
    <label class="fld" for="cf-bk"><span>Booking no GMV (%)</span><input id="cf-bk" type="number" min="0" max="100" step="1" value="35"></label>
    <label class="fld" for="cf-prem"><span>Prêmio atual (%)</span><input id="cf-prem" type="number" step="0.5" value="15"></label>
    <label class="fld" for="cf-ra0"><span>Nota Airbnb 12m · hoje</span><input id="cf-ra0" type="number" min="1" max="5" step="0.01" value="4.70"></label>
    <label class="fld" for="cf-ra1"><span>Nota Airbnb 12m · cenário</span><input id="cf-ra1" type="number" min="1" max="5" step="0.01" value="4.80"></label>
    <label class="fld" for="cf-rb0"><span>Nota Booking · hoje (0–10)</span><input id="cf-rb0" type="number" min="0" max="10" step="0.1" value="8.5"></label>
    <label class="fld" for="cf-rb1"><span>Nota Booking · cenário (0–10)</span><input id="cf-rb1" type="number" min="0" max="10" step="0.1" value="8.5"></label>
    <label class="chk wide" for="cf-usebk"><input id="cf-usebk" type="checkbox"> Incluir o efeito estimado do Booking (não significativo; o padrão é zero)</label>
  </div>
  <div class="calc-out" aria-live="polite">
    <div><span class="eyebrow">Efeito no prêmio</span><span class="v" id="cf-eff">–</span><span class="s" id="cf-band">–</span></div>
    <div><span class="eyebrow">Prêmio no cenário</span><span class="v" id="cf-new">–</span><span class="s" id="cf-pp">–</span></div>
    <div><span class="eyebrow">Versão com limiar</span><span class="v" id="cf-lim">–</span><span class="s" id="cf-limb">–</span></div>
  </div>
</div>
<script>
(function(){{
  var D = {data};
  var $ = function(id){{ return document.getElementById(id); }};
  function fmt(x, d){{ var s = Math.abs(x).toFixed(d).replace('.', ','); return (x > 0.00001 ? '+' : (x < -0.00001 ? '\\u2212' : '')) + s; }}
  function q(v, p){{ v = v.slice().sort(function(a, b){{ return a - b; }}); return v[Math.min(v.length - 1, Math.floor(p * v.length))]; }}
  function prop(c, air, dra, bk, drb, usebk){{ return Math.exp(c[0] * air * dra + (usebk ? c[1] * bk * drb : 0)) - 1; }}
  function lim(c, air, dra){{ return Math.exp(Math.max(0, c[0] + c[1] * air) * dra) - 1; }}
  function calc(){{
    var air = (+$('cf-air').value || 0) / 100, bk = (+$('cf-bk').value || 0) / 100, prem = (+$('cf-prem').value || 0) / 100;
    var dra = (+$('cf-ra1').value || 0) - (+$('cf-ra0').value || 0), drb = (+$('cf-rb1').value || 0) - (+$('cf-rb0').value || 0);
    var usebk = $('cf-usebk').checked;
    var e = prop(D.p, air, dra, bk, drb, usebk);
    var v = D.pd.map(function(c){{ return prop(c, air, dra, bk, drb, usebk); }});
    var newp = (1 + prem) * (1 + e) - 1;
    $('cf-eff').textContent = fmt(e * 100, 1) + '%';
    $('cf-band').textContent = 'intervalo de 90%: ' + fmt(q(v, .05) * 100, 1) + '% a ' + fmt(q(v, .95) * 100, 1) + '%';
    $('cf-new').textContent = fmt(newp * 100, 1) + '%';
    $('cf-pp').textContent = fmt((newp - prem) * 100, 1) + ' p.p. sobre ' + fmt(prem * 100, 1) + '%';
    var el = lim(D.l, air, dra), lv = D.ld.map(function(c){{ return lim(c, air, dra); }});
    $('cf-lim').textContent = fmt(el * 100, 1) + '%';
    $('cf-limb').textContent = 'só Airbnb; intervalo ' + fmt(q(lv, .05) * 100, 1) + '% a ' + fmt(q(lv, .95) * 100, 1) + '%';
  }}
  $('cf-predio').addEventListener('change', function(){{
    var p = D.b[this.value]; if (!p) return calc();
    $('cf-air').value = p.air; $('cf-bk').value = p.bk; $('cf-prem').value = p.prem;
    $('cf-ra0').value = p.ra.toFixed(2); $('cf-ra1').value = (p.ra + 0.1).toFixed(2);
    $('cf-rb0').value = p.rb.toFixed(1); $('cf-rb1').value = p.rb.toFixed(1); calc();
  }});
  ['cf-air','cf-bk','cf-prem','cf-ra0','cf-ra1','cf-rb0','cf-rb1','cf-usebk'].forEach(function(id){{ $(id).addEventListener('input', calc); $(id).addEventListener('change', calc); }});
  calc();
}})();
</script>'''


pa_lo, pa_hi = pctl([c[0] for c in PDR], .05), pctl([c[0] for c in PDR], .95)
pb_lo, pb_hi = pctl([c[1] for c in PDR], .05), pctl([c[1] for c in PDR], .95)
limiar = -a0 / a1
SECTION = f'''
<section>
  <div class="sec-head"><span class="eyebrow">6 · Fórmula</span><h2>Efeito no prêmio a partir do peso de cada canal e da nota</h2>
  <p class="small">Cada nota mexe na receita do próprio canal, então o efeito no prêmio é a variação da nota vezes o peso do canal no GMV do prédio. Estimada no nível do prédio (cada prédio contra ele mesmo ao longo do tempo, descontado o mês), com a nota dos últimos 12 meses. {F['final']['nb']} prédios, {F['final']['n']} prédio × mês.</p></div>
  <div class="formula panel">
    <p><b>Efeito no prêmio</b> = exp( {num(PA, 2)} × %GMV Airbnb × ΔNota Airbnb &nbsp;+&nbsp; β<sub>B</sub> × %GMV Booking × ΔNota Booking ) − 1</p>
    <p class="muted">Airbnb: nota 1–5, coeficiente {num(PA, 2)} (intervalo de 90%: {num(pa_lo, 2)} a {num(pa_hi, 2)}). Booking: nota 0–10, β<sub>B</sub> = {num(PB_, 2)} ({num(pb_lo, 2)} a {num(pb_hi, 2)}): não significativo, use 0.</p>
    <p><b>Prêmio no cenário</b> = (1 + prêmio atual) × (1 + efeito) − 1 &nbsp;<span class="muted">→ a diferença é o ganho em p.p.</span></p>
  </div>
  <ul class="bul">
    <li><b>Exemplo:</b> prédio com 50% do GMV no Airbnb e prêmio de +15%. Se a nota Airbnb dos últimos 12 meses sobe 0,1★: efeito = exp({num(PA, 2)} × 0,5 × 0,1) − 1 = {sg((math.exp(PA*.05)-1)*100)}%, e o prêmio vai a {sg(((1.15)*math.exp(PA*.05)-1)*100)}% ({sg(1.15*(math.exp(PA*.05)-1)*100)} p.p.).</li>
    <li><b>Booking:</b> a nota do prédio no Booking não mexe no prêmio em nenhuma faixa de peso. A calculadora deixa incluir a estimativa, mas o padrão é zero.</li>
    <li><b>Versão com limiar</b> (ajusta um pouco melhor, mas depende de poucos prédios com muito Airbnb): coeficiente por estrela = máx(0 ; {num(a0, 2)} + {num(a1, 2)} × %GMV Airbnb). Sem efeito abaixo de ~{num(limiar*100, 0)}% de Airbnb e mais forte acima de 60%. Mostrada na calculadora como sensibilidade. Em prédios com Airbnb abaixo de ~35% do GMV, a comparação por grupos (seção 3) não detecta efeito: ali a fórmula proporcional pode superestimar, e a versão com limiar (zero) é a mais prudente.</li>
    <li>Use para variações de até ±0,3★. Fora disso a fórmula extrapola o que os prédios mostraram. GMV aqui = receita de hospedagem por canal em 2026.</li>
  </ul>
  <h3>Sensibilidade (prêmio atual de +15%)</h3>
  {sens_table()}
  <h3>Calculadora</h3>
  {calculator()}
</section>
'''
