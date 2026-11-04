#!/usr/bin/env python3
"""Gera o slide do teste de preço base do AYR (09/set–05/out/2026).

Lê os .psv de data/ (extraídos da tabela Calendar via Metabase, ver queries.sql)
e escreve slide_ayr_teste_preco_base.html (1600x900, Viva Design System dos pitches do Growth).
Para PNG/PDF: python3 render.py
"""
import base64
import csv
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.environ.get("VIVA_LOGO", os.path.join(HERE, "logo-viva-navy.png"))


def rd(name):
    with open(os.path.join(HERE, "data", name)) as f:
        return list(csv.DictReader(f, delimiter="|"))


def br(x, nd=1):
    return f"{x:,.{nd}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, nd=1):
    return br(x * 100, nd) + "%"


def sign(x, nd=1, suf=""):
    s = br(abs(x), nd) + suf
    return ("+" if x > 0 else "−" if x < 0 else "") + s


# ---------------- dados ----------------
P = {(r["g"], r["per"]): {k: float(v) for k, v in r.items() if k not in ("g", "per")} for r in rd("periodos_estadia.psv")}
V = {(r["g"], r["per"]): {k: float(v) for k, v in r.items() if k not in ("g", "per")} for r in rd("periodos_venda.psv")}
W = rd("semanal.psv")

a0, a1, a2 = P["AYR", "1PRE"], P["AYR", "2TESTE"], P["AYR", "3POS"]
s0, s1, s2 = P["SP", "1PRE"], P["SP", "2TESTE"], P["SP", "3POS"]

d_occ = (a1["occ"] - a0["occ"]) * 100
d_occ_m = a1["mo"] - a0["mo"]
d_occ_sp = (s1["occ"] - s0["occ"]) * 100
d_adr = a1["adr"] / a0["adr"] - 1
d_adr_m = a1["mp"] / a0["mp"] - 1
prem0, prem1, prem2 = a0["adr"] / a0["mp"], a1["adr"] / a1["mp"], a2["adr"] / a2["mp"]
d_rev = a1["revpar"] / a0["revpar"] - 1
d_rev_m = a1["mrevpar"] / a0["mrevpar"] - 1
d_rev_sp = s1["revpar"] / s0["revpar"] - 1
idx0, idx1, idx2 = (p["revpar"] / p["mrevpar"] for p in (a0, a1, a2))
# contrafactual: RevPAR do teste se o AYR tivesse mantido (a) o índice vs mercado ou (b) a variação do Viva SP
cf_m = a1["mrevpar"] * idx0
cf_sp = a0["revpar"] * (1 + d_rev_sp)
loss_lo = (cf_sp - a1["revpar"]) * a1["n"]
loss_hi = (cf_m - a1["revpar"]) * a1["n"]
v0, v1, v2 = V["AYR", "1PRE"], V["AYR", "2TESTE"], V["AYR", "3POS"]
d_sold = v1["nights"] / v0["nights"] - 1
d_sold_sp = V["SP", "2TESTE"]["nights"] / V["SP", "1PRE"]["nights"] - 1

# preço base (log PriceLabs): média ponderada por unidade
BASE = [  # (unidades, antes, teste, depois)
    (8, 504, 529, 500), (3, 516, 529, 500), (6, 460, 529, 500), (9, 560, 620, 550), (3, 527, 600, 530),
    (1, 530, 575, 530), (1, 560, 620, 550), (2, 500, 575, 520), (1, 624, 670, 550), (2, 460, 529, 500)]
u = sum(b[0] for b in BASE)
base0, base1, base2 = (sum(b[0] * b[i] for b in BASE) / u for i in (1, 2, 3))

# ---------------- gráfico (SVG) ----------------
CW, CH = 860, 330
ML, MR, MT, MB = 46, 92, 18, 34
pw, ph = CW - ML - MR, CH - MT - MB
YMIN, YMAX = 40, 95
weeks = sorted({r["wk"] for r in W})
xs = {w: ML + i * pw / (len(weeks) - 1) for i, w in enumerate(weeks)}
step = pw / (len(weeks) - 1)


def y(v):
    return MT + ph * (1 - (v - YMIN) / (YMAX - YMIN))


ser = {
    "AYR": {r["wk"]: (float(r["occ"]) * 100, int(r["n"])) for r in W if r["g"] == "AYR"},
    "MKT": {r["wk"]: (float(r["mo"]), int(r["n"])) for r in W if r["g"] == "AYR"},
    "SP": {r["wk"]: (float(r["occ"]) * 100, int(r["n"])) for r in W if r["g"] == "SP"},
}
PARTIAL = {"2026-09-02", "2026-09-30", "2026-10-07"}  # semanas com noites atípicas excluídas
COL = {"AYR": "var(--terracota)", "MKT": "var(--navy)", "SP": "var(--seq-3)"}
LBL = {"AYR": "AYR", "MKT": "Mercado (compset)", "SP": "Viva SP"}


def fmt_wk(w):
    d = date.fromisoformat(w)
    m = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"][d.month - 1]
    return f"{d.day:02d}/{m}"


svg = [f'<svg viewBox="0 0 {CW} {CH}" role="img" aria-label="Ocupação semanal do AYR, do mercado e do Viva SP">']
# faixa do teste
t0, t1 = xs["2026-09-09"] - step / 2, xs["2026-09-30"] + step / 2
svg.append(f'<rect x="{t0:.1f}" y="{MT}" width="{t1 - t0:.1f}" height="{ph}" fill="rgba(196,90,61,.09)"/>')
svg.append(f'<line x1="{t0:.1f}" x2="{t0:.1f}" y1="{MT}" y2="{MT + ph}" stroke="var(--terracota)" stroke-width="1" stroke-dasharray="3 3" opacity=".7"/>')
svg.append(f'<line x1="{t1:.1f}" x2="{t1:.1f}" y1="{MT}" y2="{MT + ph}" stroke="var(--terracota)" stroke-width="1" stroke-dasharray="3 3" opacity=".7"/>')
svg.append(f'<text x="{(t0 + t1) / 2:.1f}" y="{MT + 16}" text-anchor="middle" class="ann">TESTE · BASE +{br((base1 / base0 - 1) * 100, 0)}%</text>')
svg.append(f'<text x="{(t0 + t1) / 2:.1f}" y="{MT + 31}" text-anchor="middle" class="ann2">09/set – 05/out</text>')
# grid
for v in range(40, 100, 10):
    svg.append(f'<line x1="{ML}" x2="{ML + pw}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>')
    svg.append(f'<text x="{ML - 8}" y="{y(v) + 4:.1f}" text-anchor="end" class="ax">{v}%</text>')
for i, w in enumerate(weeks):
    if i % 2 == 0:
        svg.append(f'<text x="{xs[w]:.1f}" y="{CH - 10}" text-anchor="middle" class="ax">{fmt_wk(w)}</text>')
# linhas
for k in ("SP", "MKT", "AYR"):
    pts = " ".join(f"{xs[w]:.1f},{y(ser[k][w][0]):.1f}" for w in weeks)
    dash = ' stroke-dasharray="6 5"' if k == "MKT" else ""
    sw = 3 if k == "AYR" else 2
    svg.append(f'<polyline points="{pts}" fill="none" stroke="{COL[k]}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"{dash}/>')
    for w in weeks:
        v, n = ser[k][w]
        r = 5 if k == "AYR" else 4
        hollow = w in PARTIAL
        fill = "var(--panel)" if hollow else COL[k]
        svg.append(f'<circle cx="{xs[w]:.1f}" cy="{y(v):.1f}" r="{r}" fill="{fill}" stroke="{COL[k] if hollow else "var(--panel)"}" stroke-width="2">'
                   f'<title>{LBL[k]} · semana de {fmt_wk(w)}: {br(v)}%</title></circle>')
    # rótulo direto no fim da linha
    wl = weeks[-1]
    ly = y(ser[k][wl][0]) + {"AYR": -9, "SP": 14, "MKT": 4}[k]
    svg.append(f'<text x="{xs[wl] + 10:.1f}" y="{ly:.1f}" class="dl" fill="currentColor">{LBL[k]}</text>')
# anotação do vale
wv = "2026-09-30"
svg.append(f'<text x="{xs[wv] + 10:.1f}" y="{y(ser["AYR"][wv][0]) + 5:.1f}" class="ann3">{br(ser["AYR"][wv][0], 0)}%</text>')
svg.append("</svg>")
SVG = "\n".join(svg)

# ---------------- tabela ----------------
rows = [
    ("Ocupação AYR", pct(a0["occ"]), pct(a1["occ"]), pct(a2["occ"]), True),
    ("Ocupação mercado (compset)", br(a0["mo"]) + "%", br(a1["mo"]) + "%", br(a2["mo"]) + "%", False),
    ("Vantagem vs mercado", sign(a0["occ"] * 100 - a0["mo"], 1, " p.p."), sign(a1["occ"] * 100 - a1["mo"], 1, " p.p."), sign(a2["occ"] * 100 - a2["mo"], 1, " p.p."), True),
    ("Diária média (ADR)", "R$ " + br(a0["adr"], 0), "R$ " + br(a1["adr"], 0), "R$ " + br(a2["adr"], 0), False),
    ("Prêmio de diária vs mercado", br(prem0, 2) + "x", br(prem1, 2) + "x", br(prem2, 2) + "x", True),
    ("RevPAR", "R$ " + br(a0["revpar"], 0), "R$ " + br(a1["revpar"], 0), "R$ " + br(a2["revpar"], 0), False),
    ("RevPAR vs mercado", br(idx0, 2) + "x", br(idx1, 2) + "x", br(idx2, 2) + "x", True),
    ("Noites vendidas no período¹", br(v0["nights"], 0), f'{br(v1["nights"], 0)} <span class="neg">({sign(d_sold * 100, 0, "%")})</span>', br(v2["nights"], 0), False),
    ("Viva SP · ocupação (controle)", pct(s0["occ"]), pct(s1["occ"]), pct(s2["occ"]), False),
]
TR = "\n".join(
    f'<tr class="{"key" if k else ""}"><td>{a}</td><td>{b}</td><td class="t">{c}</td><td>{d}</td></tr>' for a, b, c, d, k in rows)

logo_src = ""
if os.path.exists(LOGO):
    with open(LOGO, "rb") as f:
        logo_src = "data:image/png;base64," + base64.b64encode(f.read()).decode()

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AYR · Teste de preço base</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Jost:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
/* Viva Design System — mesmos tokens dos decks do Growth (scripts/decks/*_template.html). Slide 16:9. */
:root{{
  --navy:#0B1B2E; --terracota:#C45A3D; --ocre:#D4A574; --green:#1F7D52; --red:#A4453A;
  --creme:#F4F3F0; --panel:#FFFFFF; --sand:#E9E4DA;
  --border:rgba(11,27,46,.14); --hairline:rgba(11,27,46,.08);
  --text:rgba(11,27,46,.90); --muted:rgba(11,27,46,.58); --faint:rgba(11,27,46,.38);
  --font-display:'Newsreader',Georgia,'Times New Roman',serif;
  --font-body:'Jost',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --radius:8px; --seq-3:#487CA6; --W:1600px; --H:900px;
}}
*{{box-sizing:border-box}}
html,body{{margin:0;height:100%;background:#0B1B2E;color:var(--text);font-family:var(--font-body);-webkit-font-smoothing:antialiased;font-size:18.5px;line-height:1.45}}
h2{{font-family:var(--font-display);font-weight:500;letter-spacing:-.01em;margin:0}}
p{{margin:0}} b{{font-weight:600}}
#stage{{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;overflow:hidden}}
.slide{{position:absolute;width:var(--W);height:var(--H);left:50%;top:50%;transform:translate(-50%,-50%) scale(var(--s,1));transform-origin:center center;
  background:var(--creme);overflow:hidden;padding:52px 84px;box-shadow:0 30px 80px rgba(0,0,0,.45)}}
.eyebrow{{display:flex;align-items:center;gap:14px;font-size:12.5px;font-weight:600;letter-spacing:.16em;text-transform:uppercase;color:var(--terracota);margin:0 0 12px}}
.eyebrow::before{{content:"";width:64px;height:1px;background:var(--terracota);opacity:.7}}
.slide h2{{font-size:42px;line-height:1.08;margin-bottom:10px;max-width:1380px}}
.slide h2 .accent{{color:var(--terracota)}}
.lede{{font-size:17px;color:var(--muted);max-width:1400px;line-height:1.45;margin:0 0 20px}}
.mid{{display:grid;grid-template-columns:880px 1fr;gap:28px;align-items:stretch}}
.card{{border:1px solid var(--border);border-radius:var(--radius);background:var(--panel);padding:16px 18px 8px}}
.card-h{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px}}
.card-title{{font-size:15.5px;font-weight:600}}
.legend{{display:flex;gap:16px;font-size:12.5px;color:var(--muted)}}
.legend span{{display:inline-flex;align-items:center;gap:6px}}
.sw{{display:inline-block;width:18px;height:0;border-top:3px solid}}
svg{{display:block;width:100%;height:auto;overflow:visible;color:var(--text)}}
svg .grid{{stroke:var(--hairline);stroke-width:1}}
svg .ax{{font-size:11.5px;fill:var(--muted);font-family:var(--font-body)}}
svg .dl{{font-size:12.5px;font-weight:600;font-family:var(--font-body)}}
svg .ann{{font-size:11.5px;font-weight:600;letter-spacing:.12em;fill:var(--terracota);font-family:var(--font-body)}}
svg .ann2{{font-size:11.5px;fill:var(--muted);font-family:var(--font-body)}}
svg .ann3{{font-size:13px;font-weight:600;fill:var(--terracota);font-family:var(--font-body)}}
table{{width:100%;border-collapse:collapse;font-size:14.5px;font-variant-numeric:tabular-nums}}
th,td{{padding:7.5px 10px;text-align:right;border-bottom:1px solid var(--hairline);white-space:nowrap}}
th:first-child,td:first-child{{text-align:left}}
thead th{{font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border);vertical-align:bottom;line-height:1.3}}
thead th small{{display:block;font-weight:500;letter-spacing:.02em;text-transform:none;color:var(--faint);font-size:11px}}
thead th.t{{color:var(--terracota)}}
td.t{{background:rgba(196,90,61,.07);font-weight:600}}
tr.key td:first-child{{font-weight:600}}
.neg{{color:var(--red);font-weight:600}}
.bottom{{display:grid;grid-template-columns:1fr 520px;gap:28px;margin-top:20px}}
.strip{{display:grid;grid-template-columns:repeat(4,1fr);background:var(--navy);color:#F4F3F0;border-radius:var(--radius);padding:18px 6px}}
.strip>div{{padding:2px 20px;border-left:1px solid rgba(244,243,240,.18)}}
.strip>div:first-child{{border-left:none}}
.kpi-label{{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:rgba(244,243,240,.62);margin-bottom:8px}}
.kpi-value{{font-family:var(--font-display);font-size:38px;line-height:1;font-weight:500;color:var(--ocre)}}
.kpi-value.sm{{font-size:32px;white-space:nowrap}}
.kpi-sub{{font-size:12.5px;color:rgba(244,243,240,.66);margin-top:8px;line-height:1.4}}
.callout{{border:1px solid var(--border);border-top:3px solid var(--terracota);border-radius:var(--radius);background:var(--panel);padding:14px 20px;font-size:14px;line-height:1.48}}
.callout .tag{{font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--terracota);display:block;margin-bottom:5px}}
.callout b{{color:var(--navy)}}
.footnote{{position:absolute;left:84px;right:240px;bottom:20px;font-size:10.5px;color:var(--faint);line-height:1.45}}
.brand-corner{{position:absolute;right:84px;bottom:24px;height:18px;opacity:.9}}
@media print{{html,body{{background:none}} #stage{{position:static}} .slide{{position:relative;left:0;top:0;transform:none;box-shadow:none}} @page{{size:1600px 900px;margin:0}}}}
</style>
</head>
<body>
<div id="stage"><section class="slide">
  <div class="eyebrow">AYR 423 · Ayra Pinheiros · Teste de sensibilidade a preço</div>
  <h2>Subir o preço base em ~{br((base1 / base0 - 1) * 100, 0)}% custou <span class="accent">{br(abs(d_occ), 0)} p.p. de ocupação</span> e não aumentou a diária: o RevPAR caiu {br(abs(d_rev) * 100, 0)}% enquanto o mercado caiu {br(abs(d_rev_m) * 100, 0)}%</h2>
  <p class="lede">Entre 09/set e 05/out o preço base dos anúncios passou de R$ {br(base0, 0)} para R$ {br(base1, 0)} (média por unidade) e voltou a R$ {br(base2, 0)} em 06/out. Comparamos as mesmas {int(a0["nl"])} unidades nas 4 semanas antes e depois, contra o compset de mercado e o restante do portfólio Viva em SP, <b>sem as noites atípicas</b> (eleição de 04/out, feriados e eventos).</p>

  <div class="mid">
    <div class="card">
      <div class="card-h"><div class="card-title">Ocupação semanal, estadias de até 27 noites</div>
        <div class="legend"><span><i class="sw" style="border-color:var(--terracota)"></i>AYR</span><span><i class="sw" style="border-color:var(--navy);border-top-style:dashed"></i>Mercado (compset)</span><span><i class="sw" style="border-color:var(--seq-3);border-top-width:2px"></i>Viva SP</span></div></div>
      {SVG}
    </div>
    <div>
      <table>
        <thead><tr><th></th><th>Antes<small>10/ago – 08/set</small></th><th class="t">Teste<small>09/set – 05/out</small></th><th>Depois<small>06/out – 02/nov</small></th></tr></thead>
        <tbody>
{TR}
        </tbody>
      </table>
    </div>
  </div>

  <div class="bottom">
    <div class="strip">
      <div><div class="kpi-label">Ocupação</div><div class="kpi-value">{sign(d_occ, 1, " p.p.")}</div><div class="kpi-sub">mercado {sign(d_occ_m, 1)} · Viva SP {sign(d_occ_sp, 1)} p.p.</div></div>
      <div><div class="kpi-label">Diária realizada</div><div class="kpi-value">{sign(d_adr * 100, 1, "%")}</div><div class="kpi-sub">mercado {sign(d_adr_m * 100, 1, "%")}: prêmio estável em {br(prem0, 2)}x → {br(prem1, 2)}x</div></div>
      <div><div class="kpi-label">RevPAR</div><div class="kpi-value">{sign(d_rev * 100, 0, "%")}</div><div class="kpi-sub">mercado {sign(d_rev_m * 100, 0, "%")} · Viva SP {sign(d_rev_sp * 100, 0, "%")}</div></div>
      <div><div class="kpi-label">Receita deixada na mesa</div><div class="kpi-value sm">R$ {br(loss_lo / 1000, 0)}–{br(loss_hi / 1000, 0)} mil</div><div class="kpi-sub">hospedagem nas {br(a1["n"], 0)} noites comparáveis do teste²</div></div>
    </div>
    <div class="callout"><span class="tag">Leitura e próximo passo</span>
      O hóspede do AYR compra perto da data (mais da metade das noites é vendida na última semana) e compara preço: o aumento <b>reduziu as reservas ({sign(d_sold * 100, 0, "%")} vs Viva SP {sign(d_sold_sp * 100, 0, "%")})</b> sem elevar a diária. Com o retorno em 06/out a ocupação voltou a {pct(a2["occ"], 0)}. Vamos <b>manter o preço base atual</b> e buscar prêmio em datas de alta demanda (eventos e feriados), onde o mercado sobe e o AYR ainda ficou abaixo.
    </div>
  </div>

  <p class="footnote">Fonte: tabela Calendar (VivaAnalytics/Metabase), unidades com operação em todo o período, estadias &lt; 28 noites; mercado = compset PriceLabs (mkt_occ, mkt_price); RevPAR = diária × ocupação. Noites excluídas: feriado de 7/set (04–07/set), 1º turno das eleições (02–05/out), feriado de 12/out (10–12/out), BTS e Finados (30/out–02/nov); pontos vazados = semanas com noites excluídas. Preço base: log do PriceLabs (alterações em 08/set 22h e 06/out 13h).
  ¹ Noites de reservas criadas em cada janela de 4 semanas (Viva SP: {sign(d_sold_sp * 100, 0, "%")}). ² Diferença entre o RevPAR realizado e o RevPAR se o AYR tivesse acompanhado o Viva SP (R$ {br(loss_lo / 1000, 1)} mil) ou mantido o índice vs mercado (R$ {br(loss_hi / 1000, 1)} mil).</p>
  {f'<img class="brand-corner" src="{logo_src}" alt="viva">' if logo_src else ''}
</section></div>
<script>
function fit(){{var s=Math.min(window.innerWidth/1600,window.innerHeight/900);document.querySelector('.slide').style.setProperty('--s',s);}}
window.addEventListener('resize',fit);fit();
</script>
</body>
</html>
"""

out = os.path.join(HERE, "slide_ayr_teste_preco_base.html")
with open(out, "w") as f:
    f.write(html)
print("ok", out)
print(f"base {base0:.1f} -> {base1:.1f} ({base1 / base0 - 1:+.1%}) -> {base2:.1f}; perda {loss_lo:.0f}-{loss_hi:.0f}")
