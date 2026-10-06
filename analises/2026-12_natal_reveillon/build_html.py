import json, os
H = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(H, 'natal_reveillon.json')))
C = d['curves']
p = lambda v: f"{round(v * 100)}%"
rep = {'__DATA__': json.dumps(d, ensure_ascii=False)}
for key in ['FLN-NAT', 'FLN-REV', 'SP-NAT', 'SP-REV']:
    c = C[key]
    now, a25, a24 = c['2026']['cum'][0], c['2025']['cum'][0], c['2024']['cum'][0]
    tag = '__' + key.replace('-', '_') + '__'
    rep[tag] = f'{p(now)} <span class="small">vs {p(a25)} (2025) · {p(a24)} (2024)</span>'
    rep[tag[:-2] + '_S__'] = (f"ADR das reservas de hoje: R$ {c['2026']['adr_avg']:.0f}. Final de 2025: {p(c['2025']['final'])} de ocupação, "
                              f"RevPAR R$ {c['2025']['revpar']:.0f} (2024: R$ {c['2024']['revpar']:.0f}).")
html = open(os.path.join(H, 'head.html')).read() + open(os.path.join(H, 'body.html')).read()
for k, v in rep.items():
    html = html.replace(k, v)
open(os.path.join(H, 'relatorio_natal_reveillon.html'), 'w').write(html)
print('ok', len(html))
