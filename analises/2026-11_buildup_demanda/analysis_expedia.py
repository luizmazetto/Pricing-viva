"""Expedia: (1) demanda nova vs canibalização separando Expedia dos demais 'outros'; (2) notas da Expedia x prêmio (nível prédio)."""
import numpy as np, pandas as pd, collections
rng = np.random.default_rng(9)
D = pd.read_csv('data/historico_predio_mes.psv', sep='|')
X = pd.read_csv('data/expedia_receita_predio_mes.psv', sep='|')
D = D.merge(X, on=['b', 'm'], how='left').fillna({'rev_exp': 0})
D = D[(D.mrevpar.notna()) & (D.n >= 150) & (D.n_mkt / D.n >= 0.8)].copy()
D['w'] = D.n
for k, c in (('air', 'rev_air'), ('bk', 'rev_bk'), ('exp', 'rev_exp')): D['p_' + k] = D[c] / D.n / D.mrevpar
D['p_out'] = (D.rev_tot - D.rev_air - D.rev_bk - D.rev_exp) / D.n / D.mrevpar
D['p_ota'] = D.p_air + D.p_bk; D['p_tot'] = D.rev_tot / D.n / D.mrevpar
D['s_exp'] = D.rev_exp / D.rev_tot.replace(0, np.nan)

def fe(df, xs, y, fes=('b', 'm'), it=30):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in fes]; Z = df[xs + [y]].to_numpy(float).copy()
    for _ in range(it):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(Z.shape[1]): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    X_, Y = Z[:, :-1], Z[:, -1]
    return np.linalg.lstsq((X_ * w[:, None]).T @ X_, (X_ * w[:, None]).T @ Y, rcond=None)[0]
def boot(df, xs, y, B=400):
    b0 = fe(df, xs, y); G = {g: d for g, d in df.groupby('b')}; nm = list(G); bs = []
    for _ in range(B):
        pick = rng.choice(nm, len(nm)); bs.append(fe(pd.concat([G[k].assign(b=f'{k}#{i}') for i, k in enumerate(pick)]), xs, y))
    bs = np.array(bs)
    return {x: (round(b0[j], 3), round(np.percentile(bs[:, j], 5), 3), round(np.percentile(bs[:, j], 95), 3)) for j, x in enumerate(xs)}

print('== 1. Canais: OTA (Airbnb+Booking) e total vs Expedia e demais outros')
print('peso médio no prêmio (pontos):', {k: round(np.average(D['p_' + k], weights=D.w), 3) for k in ('air', 'bk', 'exp', 'out')})
print('OTA   :', boot(D, ['p_exp', 'p_out'], 'p_ota'))
print('Airbnb:', boot(D, ['p_exp', 'p_out'], 'p_air'))
print('total :', boot(D, ['p_exp', 'p_out'], 'p_tot'))
OC = pd.read_csv('data/ocupacao_predio_mes.psv', sep='|')[['b', 'm', 'occ']]
F = D.merge(OC, on=['b', 'm']); F['occ_b'] = F.groupby('b').occ.transform('mean')
for lab, sel in (('cheios (≥80%)', F.occ_b >= 0.8), ('com folga (<80%)', F.occ_b < 0.8)):
    d = F[sel]; print(f'  {lab} {d.b.nunique()} prédios | total:', boot(d, ['p_exp', 'p_out'], 'p_tot', B=300))

print('\n== 2. Notas da Expedia x prêmio (nível prédio, prédio + mês)')
R = pd.read_csv('data/reviews_expedia_predio_mes.psv', sep='|')
mi = lambda m: int(m[:4]) * 12 + int(m[5:7]) - 1
R['t'] = R.m.map(mi); D['t'] = D.m.map(mi)
print('reviews Expedia por ano:', R.groupby(R.m.str[:4]).n.sum().to_dict(), '| nota média', round(R.sg.sum() / R.n.sum(), 2))
def win(bdf, t, k):
    x = bdf[(bdf.t <= t - 1) & (bdf.t > t - 1 - k)] if k else bdf[bdf.t <= t - 1]
    return (x.sg.sum() / x.n.sum(), x.n.sum()) if x.n.sum() else (np.nan, 0)
G = {b: g for b, g in R.groupby('b')}
for lab, k, mn in (('acumulada', None, 10), ('24 meses', 24, 8), ('12 meses', 12, 5)):
    vals = [win(G[b], t, k) if b in G else (np.nan, 0) for b, t in zip(D.b, D.t)]
    D['re'] = [v if n >= mn else np.nan for v, n in vals]
    d = D.dropna(subset=['re']).copy(); d['lp'] = np.log(d.p_tot)
    d['x'] = d.re * d.s_exp.fillna(0)
    r1 = boot(d, ['re'], 'lp', B=300); r2 = boot(d, ['x'], 'lp', B=300)
    print(f'  {lab:10s} {d.b.nunique()} prédios, {len(d)} prédio×mês | por estrela: {r1["re"]} | por estrela × %Expedia: {r2["x"]} | %Expedia médio {np.average(d.s_exp.fillna(0), weights=d.w):.1%}')
