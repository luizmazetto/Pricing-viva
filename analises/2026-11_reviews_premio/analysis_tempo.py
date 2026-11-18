"""Nota × prêmio ao longo do tempo (mesmo prédio / mesmo anúncio), por janela de reviews e canal. Gera tempo.json."""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(5)
mi = lambda m: int(m[:4]) * 12 + int(m[5:7]) - 1
P = pd.read_csv('data/premio_master_month.psv', sep='|'); BLD = sorted(set(P.b))
R = pd.read_csv('data/reviews_master_month.psv', sep='|'); R = R[R.b.isin(BLD)]
K = pd.read_csv('data/reviews_booking_master_month.psv', sep='|'); K = K[K.b.isin(BLD)]
CH = pd.read_csv('data/canal_master_month.psv', sep='|')
T0, T1 = mi('2022-12'), mi('2026-11'); ALLT = np.arange(T0, T1 + 1); ix = {t: i for i, t in enumerate(ALLT)}

def mat(df, key):
    keys = sorted(df[key].dropna().unique()); pos = {k: i for i, k in enumerate(keys)}
    n = np.zeros((len(keys), len(ALLT))); s = np.zeros_like(n)
    for r in df.itertuples():
        k = getattr(r, key)
        if k in pos: n[pos[k], ix[mi(r.m)]] += r.n; s[pos[k], ix[mi(r.m)]] += r.sg
    return keys, pos, n, s
def win(n, s, k):
    cn, cs = np.cumsum(n, 1), np.cumsum(s, 1)
    if k is None: return cn, cs
    a, b = cn.copy(), cs.copy(); a[:, k:] -= cn[:, :-k]; b[:, k:] -= cs[:, :-k]; return a, b
def ew(n, s, h):
    d = 0.5 ** (1 / h); N = np.zeros_like(n); S = np.zeros_like(s)
    for j in range(n.shape[1]):
        N[:, j] = n[:, j] + (d * N[:, j - 1] if j else 0); S[:, j] = s[:, j] + (d * S[:, j - 1] if j else 0)
    return N, S
def lead(n, s, k):
    cn, cs = np.cumsum(n, 1), np.cumsum(s, 1); N = np.zeros_like(n); S = np.zeros_like(s)
    for j in range(n.shape[1]):
        hi = min(j + k, n.shape[1] - 1); N[:, j] = cn[:, hi] - cn[:, j]; S[:, j] = cs[:, hi] - cs[:, j]
    return N, S
def fe(df, xs, y, fes, it=30):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in fes]; Z = df[xs + [y]].to_numpy(float).copy()
    for _ in range(it):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(Z.shape[1]): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    X, Y = Z[:, :-1], Z[:, -1]
    b = np.linalg.lstsq((X * w[:, None]).T @ X, (X * w[:, None]).T @ Y, rcond=None)[0]
    return b, float(1 - np.sum(w * (Y - X @ b) ** 2) / np.sum(w * Y ** 2)), float(np.sqrt(np.sum(w * X[:, 0] ** 2) / w.sum()))
def boot(df, xs, y, fes, cl, B=300):
    b0, r2, sd = fe(df, xs, y, fes); G = {g: d for g, d in df.groupby(cl)}; names = list(G); bs = []
    for _ in range(B):
        pick = rng.choice(names, len(names))
        dd = pd.concat([G[k].assign(**{f: G[k][f].astype(str) + f'#{i}' for f in fes if f != 'm'}) for i, k in enumerate(pick)])
        bs.append(fe(dd, xs, y, fes)[0])
    bs = np.array(bs)
    return [dict(b=float(b0[j]), lo=float(np.percentile(bs[:, j], 5)), hi=float(np.percentile(bs[:, j], 95)),
                 p01=float(np.exp(b0[j] * .1) - 1), p01_lo=float(np.exp(np.percentile(bs[:, j], 5) * .1) - 1),
                 p01_hi=float(np.exp(np.percentile(bs[:, j], 95) * .1) - 1)) for j in range(len(xs))], r2, sd

# ---------------- painel prédio × mês
PB = P[P.mrevpar > 0].assign(rw=lambda d: d.rev * d.n, mw=lambda d: d.mrevpar * d.n).groupby(['b', 'm']).agg(rw=('rw', 'sum'), mw=('mw', 'sum'), w=('n', 'sum')).reset_index()
PB = PB[PB.w >= 150].copy(); PB['lp'] = np.log(PB.rw / PB.mw); PB = PB[np.isfinite(PB.lp)]
bk, bpos, bn, bs_ = mat(R, 'b'); kk, kpos, kn, ks = mat(K, 'b')
PB['bi'] = PB.b.map(bpos); PB['ti'] = PB.m.map(lambda m: ix[mi(m)] - 1)    # nota até o fim do mês anterior
PB = PB.dropna(subset=['bi']); PB['bi'] = PB.bi.astype(int)
first = np.argmax(bn > 0, axis=1); PB['age'] = PB.ti - first[PB.bi]
CB = CH[CH.m >= '2026-01'].groupby('b')[['rev_airbnb', 'rev_booking', 'rev_total']].sum()
PB['air'] = PB.b.map(CB.rev_airbnb / CB.rev_total); PB['bks'] = PB.b.map(CB.rev_booking / CB.rev_total)

def rating(n, s, pos, df, kind, arg, minN, col='b'):
    if kind == 'win': N, S = win(n, s, arg)
    elif kind == 'ew': N, S = ew(n, s, arg)
    else: N, S = lead(n, s, arg)
    i = df[col].map(pos); ok = i.notna(); i = i.fillna(0).astype(int).to_numpy()
    t = df.ti.to_numpy() + (1 if kind == 'lead' else 0)
    v = N[i, t]; return np.where(ok & (v >= minN), S[i, t] / np.where(v > 0, v, 1), np.nan)

WINS = [('Acumulada (nota exibida)', 'win', None, 30), ('Últimos 24 meses', 'win', 24, 20), ('Últimos 12 meses', 'win', 12, 15),
        ('Últimos 6 meses', 'win', 6, 10), ('Últimos 3 meses', 'win', 3, 8), ('Meia-vida 3 meses', 'ew', 3, 8), ('Meia-vida 6 meses', 'ew', 6, 10),
        ('Meia-vida 12 meses', 'ew', 12, 15), ('Meia-vida 24 meses', 'ew', 24, 20), ('Próximos 3 meses (placebo)', 'lead', 3, 8)]
for lab, kind, arg, mn in WINS:
    PB[lab] = rating(bn, bs_, bpos, PB, kind, arg, mn)
    PB['BK ' + lab] = rating(kn, ks, kpos, PB, kind, arg, max(5, mn // 2)) / 2      # Booking em "estrelas"
labs = [w[0] for w in WINS]
common = PB.dropna(subset=labs).copy()
out = {'n_predio_mes': int(len(common)), 'n_predios': int(common.b.nunique())}

def run(df, cols, groups=None):
    res = []
    for l in cols:
        d = df.dropna(subset=[l]).rename(columns={l: 'x'})
        e, r2, sd = boot(d, ['x'], 'lp', ['b', 'm'], 'b')
        res.append(dict(lab=l, n=int(len(d)), nb=int(d.b.nunique()), est=e[0], r2=r2, sd=sd, p_sd=float(np.exp(e[0]['b'] * sd) - 1)))
    return res
out['predio_airbnb'] = run(common, labs)
out['predio_booking'] = run(common.dropna(subset=['BK ' + l for l in labs[:-1]]), ['BK ' + l for l in labs])
# maduros (≥ 12 meses de reviews) e novos
out['predio_maduro'] = run(common[common.age >= 12], ['Acumulada (nota exibida)', 'Últimos 12 meses', 'Últimos 6 meses', 'Meia-vida 6 meses'])
out['predio_novo'] = run(PB[(PB.age < 12)].dropna(subset=['Últimos 6 meses']), ['Acumulada (nota exibida)', 'Últimos 6 meses'])
out['n_novo'] = int((PB.age < 12).sum())
# os dois canais juntos, com interação pelo peso do canal (nível prédio, nota acumulada e 12 meses)
for lab in ('Acumulada (nota exibida)', 'Últimos 12 meses'):
    d = common.dropna(subset=['BK ' + lab, 'air', 'bks']).copy()
    d['xa'] = d[lab]; d['xb'] = d['BK ' + lab]; d['xa_s'] = d.xa * (d.air - .45); d['xb_s'] = d.xb * (d.bks - .35)
    e, r2, _ = boot(d, ['xa', 'xb', 'xa_s', 'xb_s'], 'lp', ['b', 'm'], 'b', B=300)
    out['conjunto_' + lab] = dict(zip(['xa', 'xb', 'xa_s', 'xb_s'], e)); out['conjunto_n'] = int(len(d))
# dimensão: ocupação × diária (nível prédio, acumulada)
PO = P[P.mrevpar > 0].assign(o=lambda d: d.occ * d.n, mo_=lambda d: d.mo * d.n).groupby(['b', 'm']).agg(o=('o', 'sum'), mo_=('mo_', 'sum')).reset_index()
c2 = common.merge(PO, on=['b', 'm']); c2['locc'] = np.log(c2.o / c2.mo_); c2['ladr'] = c2.lp - c2.locc
for y in ('locc', 'ladr'):
    d = c2.rename(columns={'Acumulada (nota exibida)': 'x'}); e, _, _ = boot(d, ['x'], y, ['b', 'm'], 'b', B=200); out['dim_' + y] = e[0]
# defasagens (nota acumulada de k meses atrás) e antecedência
lag = []
for k in (1, 3, 6, 9, 12):
    d = PB.copy(); d['ti'] = d.ti - (k - 1); d = d[d.ti >= 0]
    d['x'] = rating(bn, bs_, bpos, d, 'win', None, 30); d = d.dropna(subset=['x'])
    e, _, _ = boot(d, ['x'], 'lp', ['b', 'm'], 'b', B=200); lag.append(dict(k=k, n=int(len(d)), est=e[0]))
out['defasagem'] = lag

# peso do Airbnb: prédios com Airbnb >= 50% da receita vs < 50%
out['split_air'] = {}
for lab_g, sel in (('Airbnb ≥ 50% da receita', common.air >= 0.5), ('Airbnb < 50% da receita', common.air < 0.5)):
    d = common[sel]
    out['split_air'][lab_g] = dict(nb=int(d.b.nunique()), res=run(d, ['Acumulada (nota exibida)', 'Últimos 12 meses', 'Últimos 6 meses']),
                                   bk=run(d.dropna(subset=['BK Acumulada (nota exibida)']), ['BK Acumulada (nota exibida)', 'BK Últimos 12 meses']))
# gráfico: desvio da nota do prédio (vs a própria média e o mês) × desvio do prêmio
def resid(df, x, y):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in ('b', 'm')]; Z = df[[x, y]].to_numpy(float).copy()
    for _ in range(30):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(2): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    return Z[:, 0], Z[:, 1], w
X, Y, W = resid(common, 'Últimos 12 meses', 'lp')
q = np.quantile(X, [0, .1, .3, .5, .7, .9, 1]); q[0] -= 1; q[-1] += 1; cut = np.digitize(X, q[1:-1])
out['bins_predio'] = [dict(x=float(np.average(X[cut == i], weights=W[cut == i])), y=float(np.exp(np.average(Y[cut == i], weights=W[cut == i])) - 1), n=int((cut == i).sum())) for i in range(6)]

# série para o gráfico: prédios same store, médias do portfólio (desvios em relação à média do prédio)
json.dump(out, open('tempo.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
for k in ('predio_airbnb', 'predio_booking', 'predio_maduro', 'predio_novo'):
    print('==', k)
    for r in out[k]: print(f"  {r['lab']:32s} n={r['n']} nb={r['nb']} {r['est']['p01']*100:+.2f}% [{r['est']['p01_lo']*100:+.1f},{r['est']['p01_hi']*100:+.1f}] r2 {r['r2']:.3f} sd {r['sd']:.3f} p/sd {r['p_sd']*100:+.2f}%")
for k in ('conjunto_Acumulada (nota exibida)', 'conjunto_Últimos 12 meses'):
    print(k, {a: (round(v['b'], 3), round(v['lo'], 3), round(v['hi'], 3)) for a, v in out[k].items()})
print('dim', {k: round(out[k]['p01'] * 100, 2) for k in ('dim_locc', 'dim_ladr')})
for g,v in out['split_air'].items():
    print(g, v['nb'], [(r['lab'], round(r['est']['p01']*100,2), round(r['est']['p01_lo']*100,1), round(r['est']['p01_hi']*100,1)) for r in v['res']+v['bk']])
print(out['bins_predio'])
for r in lag: print('lag', r['k'], r['n'], round(r['est']['p01'] * 100, 2), round(r['est']['p01_lo'] * 100, 2), round(r['est']['p01_hi'] * 100, 2))
