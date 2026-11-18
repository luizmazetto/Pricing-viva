"""Booking: efeito de cruzar faixas de nota (8,0 e 9,0) no prêmio, nível prédio. Nota Booking = média 36 meses (regra do Booking)."""
import numpy as np, pandas as pd, collections
rng = np.random.default_rng(13)
mi = lambda m: int(m[:4]) * 12 + int(m[5:7]) - 1
RB = pd.read_csv('../2026-11_reviews_premio/data/reviews_booking_master_month.psv', sep='|')
RB['c'] = RB.b.str.split(' - ').str[0].str.strip(); RB['t'] = RB.m.map(mi)
G = RB.groupby(['c', 't'])[['n', 'sg']].sum()
D = pd.read_csv('data/historico_predio_mes.psv', sep='|')
D = D[(D.mrevpar.notna()) & (D.n >= 150) & (D.n_mkt / D.n >= 0.8)].copy()
D['c'] = D.b.str.split(' - ').str[0].str.strip(); D['t'] = D.m.map(mi); D['w'] = D.n
D['p_tot'] = D.rev_tot / D.n / D.mrevpar; D['lp'] = np.log(D.p_tot)
D['p_bk'] = D.rev_bk / D.n / D.mrevpar; D['s_bk'] = D.rev_bk / D.rev_tot
def score(c, t, k=36):
    try: g = G.loc[c]
    except KeyError: return np.nan, 0
    x = g[(g.index <= t - 1) & (g.index > t - 1 - k)]
    return (x.sg.sum() / x.n.sum(), x.n.sum()) if x.n.sum() else (np.nan, 0)
sc = [score(c, t) for c, t in zip(D.c, D.t)]
D['bk'] = [s if n >= 10 else np.nan for s, n in sc]; D['bk_n'] = [n for _, n in sc]
D = D.dropna(subset=['bk']).copy()
D['f8'] = (D.bk >= 8.0).astype(float); D['f9'] = (D.bk >= 9.0).astype(float); D['f7'] = (D.bk >= 7.0).astype(float)
print('prédio×mês', len(D), 'prédios', D.c.nunique())
print('distribuição da nota (prédio×mês):', pd.cut(D.bk, [0, 7, 8, 8.5, 9, 10]).value_counts().sort_index().to_dict())
# quem cruzou faixas
cross = []
for c, g in D.sort_values('t').groupby('c'):
    for thr in (8.0, 9.0):
        a = (g.bk >= thr).astype(int).diff().fillna(0)
        if (a != 0).any(): cross.append((c, thr, int((a > 0).sum()), int((a < 0).sum()), round(g.bk.min(), 2), round(g.bk.max(), 2)))
print('cruzamentos (prédio, faixa, entradas, saídas, min, max):'); [print('  ', x) for x in cross]

def fe(df, xs, y, fes=('c', 'm'), it=30):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in fes]; Z = df[xs + [y]].to_numpy(float).copy()
    for _ in range(it):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(Z.shape[1]): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    X, Y = Z[:, :-1], Z[:, -1]
    return np.linalg.lstsq((X * w[:, None]).T @ X, (X * w[:, None]).T @ Y, rcond=None)[0]
def boot(df, xs, y, B=400):
    b0 = fe(df, xs, y); Gs = {g: d for g, d in df.groupby('c')}; nm = list(Gs); bs = []
    for _ in range(B):
        pick = rng.choice(nm, len(nm)); bs.append(fe(pd.concat([Gs[k].assign(c=f'{k}#{i}') for i, k in enumerate(pick)]), xs, y))
    bs = np.array(bs)
    return {x: (round(b0[j], 3), round(np.percentile(bs[:, j], 5), 3), round(np.percentile(bs[:, j], 95), 3)) for j, x in enumerate(xs)}
print('\nprêmio total (log) ~ acima de 8,0 / 9,0 [prédio + mês]:', boot(D, ['f8', 'f9'], 'lp'))
D['f8s'] = D.f8 * D.s_bk.fillna(0); D['f9s'] = D.f9 * D.s_bk.fillna(0)
print('prêmio total (log) ~ faixa × %Booking:', boot(D, ['f8s', 'f9s'], 'lp'))
print('prêmio via Booking (pontos) ~ acima de 8,0 / 9,0:', boot(D, ['f8', 'f9'], 'p_bk'))
print('prêmio via Booking ~ faixa + nota contínua:', boot(D.assign(bkc=D.bk), ['f8', 'f9', 'bkc'], 'p_bk'))
D['p_air'] = D.rev_air / D.n / D.mrevpar
print('\nprêmio via Airbnb (pontos) ~ acima de 8,0 / 9,0:', boot(D, ['f8', 'f9'], 'p_air'))
print('prêmio total (pontos) ~ acima de 8,0 / 9,0:', boot(D, ['f8', 'f9'], 'p_tot'))
print('pontos médios: total', round(np.average(D.p_tot, weights=D.w), 3), 'Booking', round(np.average(D.p_bk, weights=D.w), 3), 'Airbnb', round(np.average(D.p_air, weights=D.w), 3))
for lab, sel in (('Booking ≥ 35% da receita', D.groupby('c').s_bk.transform('mean') >= 0.35), ('Booking < 35%', D.groupby('c').s_bk.transform('mean') < 0.35)):
    d = D[sel]; print(f'  {lab}: {d.c.nunique()} prédios | total (log):', boot(d, ['f8'], 'lp', B=300), '| via Booking:', boot(d, ['f8'], 'p_bk', B=300))
