import json, os
H = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(H, 'recomendacoes.json')))
def agg(ev):
    t = sum(x['unit_nights'] for x in d[ev])
    return (sum(x['unit_nights']*x['occ'] for x in d[ev])/t, sum(x['unit_nights']*x['mkt_occ'] for x in d[ev])/t, sum(x['remaining'] for x in d[ev]))
p = lambda v: f"{round(v*100)}%"
bo, bm, br = agg('BTS'); fo, fm, fr = agg('F1')
# Curva F1 2025 (sem mid-term): noites por janela de antecedência, total 1624
buckets = [('61+',56,485),('34–60',55,462),('22–33',106,474),('15–21',172,383),('8–14',557,403),('0–7',646,528)]
tot = 1624; cum = 0
W, Hh, L, B = 520, 250, 46, 200
bw = (W - L - 20) / len(buckets)
svg = [f'<svg viewBox="0 0 {W} {Hh}" role="img" aria-label="Ocupação acumulada da F1 2025 por antecedência da reserva">']
for g in (0, .25, .5, .75, 1):
    y = B - g*170
    svg.append(f'<line x1="{L}" x2="{W-10}" y1="{y:.1f}" y2="{y:.1f}" stroke="var(--line)"/><text x="{L-6}" y="{y+4:.1f}" font-size="11" text-anchor="end" fill="var(--muted)" font-family="JetBrains Mono, monospace">{int(g*100)}%</text>')
for i, (lab, n, adr) in enumerate(buckets):
    cum += n; c = cum/tot
    x = L + 10 + i*bw; h = c*170
    svg.append(f'<rect x="{x:.1f}" y="{B-h:.1f}" width="{bw-16:.1f}" height="{h:.1f}" rx="3" fill="var(--f1)" opacity="{0.35+0.65*(i+1)/len(buckets):.2f}"/>')
    svg.append(f'<text x="{x+(bw-16)/2:.1f}" y="{B-h-18:.1f}" font-size="11.5" text-anchor="middle" fill="var(--ink)" font-weight="600" font-family="JetBrains Mono, monospace">{round(c*100)}%</text>')
    svg.append(f'<text x="{x+(bw-16)/2:.1f}" y="{B-h-5:.1f}" font-size="10" text-anchor="middle" fill="var(--muted)" font-family="JetBrains Mono, monospace">R${adr}</text>')
    svg.append(f'<text x="{x+(bw-16)/2:.1f}" y="{B+16:.1f}" font-size="11" text-anchor="middle" fill="var(--muted)" font-family="JetBrains Mono, monospace">{lab}</text>')
    if lab == '34–60':
        yn = B - 0.089*170
        svg.append(f'<circle cx="{x+(bw-16)/2:.1f}" cy="{yn:.1f}" r="5" fill="var(--f1)" stroke="var(--surface)" stroke-width="2"/><text x="{x+(bw-16)/2+9:.1f}" y="{yn+20:.1f}" font-size="11" fill="var(--f1)" font-weight="600" font-family="JetBrains Mono, monospace">2026 hoje: 8,9%</text>')
svg.append(f'<text x="{(L+W)/2:.0f}" y="{B+36}" font-size="11" text-anchor="middle" fill="var(--muted)">dias antes da corrida em que a reserva foi criada (cumulativo até a janela)</text></svg>')
html = open(os.path.join(H, 'template.html')).read()
for k, v in {'__BTS_OCC__': p(bo), '__BTS_MKT__': p(bm), '__BTS_REM__': f"{br:,}".replace(',', '.'),
             '__F1_OCC__': p(fo), '__F1_MKT__': p(fm), '__CURVE__': ''.join(svg),
             '__DATA__': json.dumps(d, ensure_ascii=False)}.items():
    html = html.replace(k, v)
open(os.path.join(H, 'relatorio_sp_bts_f1.html'), 'w').write(html)
print(p(bo), p(bm), br, p(fo), p(fm), fr)
