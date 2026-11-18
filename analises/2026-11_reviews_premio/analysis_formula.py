"""Fórmula: efeito no prêmio a partir do peso de Airbnb/Booking no GMV e da variação de cada nota (nível prédio). Gera formula.json."""
import json, numpy as np, pandas as pd
src = open('analysis_tempo.py', encoding='utf-8').read().split("out = {'n_predio_mes'")[0]
exec(src)
rng = np.random.default_rng(21)
res = {}
specs = {
  'acumulada': ('Acumulada (nota exibida)', 'BK Acumulada (nota exibida)'),
  '12m': ('Últimos 12 meses', 'BK Últimos 12 meses'),
}
for key, (la, lb) in specs.items():
    d = PB.dropna(subset=[la, lb, 'air', 'bks']).copy()
    d['xa'] = d.air * d[la]                    # Airbnb: estrelas (1–5) × peso do Airbnb
    d['xb'] = d.bks * d[lb] * 2                # Booking: pontos (0–10) × peso do Booking
    e, r2, _ = boot(d, ['xa', 'xb'], 'lp', ['b', 'm'], 'b', B=400)
    # modelo livre (para comparar): nota + nota × peso, cada canal
    d['ra'] = d[la]; d['rb'] = d[lb] * 2; d['ra_s'] = d.ra * d.air; d['rb_s'] = d.rb * d.bks
    e2, r22, _ = boot(d, ['ra', 'ra_s', 'rb', 'rb_s'], 'lp', ['b', 'm'], 'b', B=400)
    res[key] = dict(n=int(len(d)), nb=int(d.b.nunique()), r2=r2, r2_livre=r22,
                    ba=e[0], bb=e[1], livre=dict(zip(['ra', 'ra_s', 'rb', 'rb_s'], e2)))
# fórmula escolhida: livre, nota dos últimos 12 meses — guarda os sorteios do bootstrap para a calculadora
d = PB.dropna(subset=['Últimos 12 meses', 'BK Últimos 12 meses', 'air', 'bks']).copy()
d['ra'] = d['Últimos 12 meses']; d['rb'] = d['BK Últimos 12 meses'] * 2; d['ra_s'] = d.ra * d.air; d['rb_s'] = d.rb * d.bks
xs = ['ra', 'ra_s', 'rb', 'rb_s']
b0 = fe(d, xs, 'lp', ['b', 'm'])[0]; G = {g: x for g, x in d.groupby('b')}; names = list(G); draws = []
for _ in range(500):
    pick = rng.choice(names, len(names))
    dd = pd.concat([G[k].assign(b=f'{k}#{i}') for i, k in enumerate(pick)])
    draws.append([round(float(v), 4) for v in fe(dd, xs, 'lp', ['b', 'm'])[0]])
res['final'] = dict(coef=[float(v) for v in b0], draws=draws, n=int(len(d)), nb=int(d.b.nunique()))
d['xa'] = d.air * d.ra; d['xb'] = d.bks * d.rb
p0 = fe(d, ['xa', 'xb'], 'lp', ['b', 'm'])[0]; pdraws = []
for _ in range(500):
    pick = rng.choice(names, len(names))
    G2 = {g: x for g, x in d.groupby('b')}
    dd = pd.concat([G2[k].assign(b=f'{k}#{i}') for i, k in enumerate(pick)])
    pdraws.append([round(float(v), 4) for v in fe(dd, ['xa', 'xb'], 'lp', ['b', 'm'])[0]])
res['prop'] = dict(coef=[float(v) for v in p0], draws=pdraws)
# dados para a calculadora: peso dos canais, prêmio e notas atuais por prédio
RV = json.load(open('reviews.json', encoding='utf-8'))
cur = []
last = PB.m.max()
for b, x in RV['bld'].items():
    if not x.get('air_share') or x['n_total'] < 30: continue
    row = PB[(PB.b == b) & (PB.m == last)]
    bk_now = float(row['BK Acumulada (nota exibida)'].iloc[0] * 2) if len(row) and pd.notna(row['BK Acumulada (nota exibida)'].iloc[0]) else None
    cur.append(dict(b=b, city=x['city'], air=x['air_share'], bk=x.get('bk_share') or 0, prem=x['prem26'],
                    ra=x['exib_oct26'], rb=bk_now, ra12=x['r12_oct26'], rb26=x['bk26']))
res['predios'] = sorted(cur, key=lambda r: r['b'])
json.dump(res, open('formula.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
for k in specs:
    r = res[k]
    print(k, 'n', r['n'], 'nb', r['nb'], 'r2', round(r['r2'], 4), 'r2 livre', round(r['r2_livre'], 4))
    print('  ba', {kk: round(v, 3) for kk, v in r['ba'].items() if kk in ('b', 'lo', 'hi')}, ' bb', {kk: round(v, 3) for kk, v in r['bb'].items() if kk in ('b', 'lo', 'hi')})
    print('  livre', {kk: (round(v['b'], 3), round(v['lo'], 3), round(v['hi'], 3)) for kk, v in r['livre'].items()})
