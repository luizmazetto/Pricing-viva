"""Robustez: isola características da unidade e testa janelas de review. Gera robustez.json."""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(11)
R = pd.read_csv('data/reviews_master_month.psv', sep='|')
P = pd.read_csv('data/premio_master_month.psv', sep='|')
C = pd.read_csv('data/caracteristicas_master.psv', sep='|')
C['m2'] = pd.to_numeric(C.m2, errors='coerce')
BLD = sorted(set(P.b)); R = R[R.b.isin(BLD)]
mi = lambda m: int(m[:4]) * 12 + int(m[5:7]) - 1
R['t'] = R.m.map(mi); P['t'] = P.m.map(mi)
T0, T1 = mi('2022-12'), mi('2026-11')
masters = R.master.unique(); ALLT = np.arange(T0, T1 + 1)
idx = {t: i for i, t in enumerate(ALLT)}
n = np.zeros((len(masters), len(ALLT))); s = np.zeros_like(n)
mpos = {m: i for i, m in enumerate(masters)}
for r in R.itertuples():
    n[mpos[r.master], idx[r.t]] += r.n; s[mpos[r.master], idx[r.t]] += r.sg

def window(k):          # últimos k meses até o fim de t (inclusive)
    cn = np.cumsum(n, 1); cs = np.cumsum(s, 1)
    if k is None: return cn, cs
    cn2 = cn.copy(); cs2 = cs.copy(); cn2[:, k:] -= cn[:, :-k]; cs2[:, k:] -= cs[:, :-k]
    return cn2, cs2
def ew(h):              # média com peso exponencial, meia-vida h meses
    dlt = 0.5 ** (1 / h); N = np.zeros_like(n); S = np.zeros_like(s)
    for j in range(len(ALLT)):
        N[:, j] = n[:, j] + (dlt * N[:, j - 1] if j else 0); S[:, j] = s[:, j] + (dlt * S[:, j - 1] if j else 0)
    return N, S
def lead(k):            # próximos k meses (placebo)
    cn = np.cumsum(n, 1); cs = np.cumsum(s, 1); N = np.zeros_like(n); S = np.zeros_like(s)
    for j in range(len(ALLT)):
        hi = min(j + k, len(ALLT) - 1)
        N[:, j] = cn[:, hi] - cn[:, j]; S[:, j] = cs[:, hi] - cs[:, j]
    return N, S

D = P[(P.n >= 20) & (P.mrevpar > 0)].copy()
D['prem'] = D.rev / D.mrevpar; D = D[D.prem > 0].copy()
D['lp'] = np.log(D.prem); D['w'] = D.n; D['bm'] = D.b + D.m
D = D[D.master.notna() & D.master.isin(mpos)].copy()
D['mi'] = D.master.map(mpos); D['ti'] = D.t.map(idx) - 1       # nota até o fim do mês anterior
D = D[D.ti >= 0]
D = D.merge(C[['master', 'rooms', 'baths', 'guests', 'm2']], on='master', how='left')
D['lm2'] = np.log(D.m2.clip(lower=10)); D['bmr'] = D.bm + '|' + D.rooms.astype(str)
cn, cs = window(None)
D['N'] = cn[D.mi, D.ti]; D['rat'] = cs[D.mi, D.ti] / np.where(D.N > 0, D.N, np.nan)
base = D[(D.N >= 10)].copy()

def ols_fe(df, xs, y, fes, it=25):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in fes]
    Z = df[xs + [y]].to_numpy(float).copy()
    for _ in range(it if len(fes) > 1 else 1):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(Z.shape[1]): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    X, Y = Z[:, :-1], Z[:, -1]
    b = np.linalg.lstsq((X * w[:, None]).T @ X, (X * w[:, None]).T @ Y, rcond=None)[0]
    r2 = 1 - np.sum(w * (Y - X @ b) ** 2) / np.sum(w * Y ** 2)
    return b, r2, np.sqrt(np.sum(w * X[:, 0] ** 2) / w.sum())
def boot(df, xs, y, fes, B=150):
    b0, r2, sdx = ols_fe(df, xs, y, fes); G = {g: d for g, d in df.groupby('b')}; names = list(G); bs = []
    for _ in range(B):
        pick = rng.choice(names, len(names))
        dd = pd.concat([G[k].assign(b=f'{k}#{i}', bm=G[k].bm + f'#{i}', bmr=G[k].bmr + f'#{i}', master=G[k].master + f'#{i}') for i, k in enumerate(pick)])
        bs.append(ols_fe(dd, xs, y, fes)[0])
    bs = np.array(bs)
    return [dict(b=float(b0[j]), lo=float(np.percentile(bs[:, j], 5)), hi=float(np.percentile(bs[:, j], 95)),
                 p01=float(np.exp(b0[j] * .1) - 1), p01_lo=float(np.exp(np.percentile(bs[:, j], 5) * .1) - 1), p01_hi=float(np.exp(np.percentile(bs[:, j], 95) * .1) - 1))
            for j in range(len(xs))], float(r2), float(sdx)

out = {}
# ---------- A. isolando características da unidade
A = base.dropna(subset=['rooms', 'baths', 'guests', 'lm2'])
spec = {}
spec['1_predio_mes'] = boot(A, ['rat'], 'lp', ['bm'])
spec['2_mesma_categoria'] = boot(A, ['rat'], 'lp', ['bmr'])
spec['3_categoria_m2_banh_hosp'] = boot(A, ['rat', 'lm2', 'baths', 'guests'], 'lp', ['bmr'])
first = np.argmax(n > 0, axis=1)
for df_ in (A, base, D):
    df_['age'] = df_.ti - first[df_.mi]; df_['lN'] = np.log(df_.N.clip(lower=1))
spec['3b_mais_volume_reviews'] = boot(A, ['rat', 'lm2', 'baths', 'guests', 'lN'], 'lp', ['bmr'])
spec['4_mesmo_anuncio'] = boot(A, ['rat'], 'lp', ['bm', 'master'])
spec['5_mesmo_anuncio_jovem'] = boot(A[A.age < 12], ['rat'], 'lp', ['bm', 'master'])
spec['6_mesmo_anuncio_maduro'] = boot(A[A.age >= 12], ['rat'], 'lp', ['bm', 'master'])
NS = {'5_mesmo_anuncio_jovem': int((A.age < 12).sum()), '6_mesmo_anuncio_maduro': int((A.age >= 12).sum())}
out['isolamento'] = {k: dict(est=v[0][0], r2=v[1], n=NS.get(k, int(len(A))), m2=(v[0][1] if len(v[0]) > 1 else None)) for k, v in spec.items()}
out['sd_rat_maduro'] = float(ols_fe(A[A.age >= 12], ['rat'], 'lp', ['bm', 'master'])[2]); out['sd_rat_jovem'] = float(ols_fe(A[A.age < 12], ['rat'], 'lp', ['bm', 'master'])[2])
# correlação nota × m² dentro do prédio-mês (a nota é maior em unidade maior?)
Z = A.copy()
for col in ('rat', 'lm2'):
    Z[col + '_d'] = Z[col] - Z.groupby('bmr')[col].transform('mean')
out['corr_nota_m2'] = float(np.corrcoef(Z.rat_d, Z.lm2_d)[0, 1])

# antes × depois: anúncios cuja nota mudou entre o começo de 2025 e o meio de 2026
def period(df, lo, hi):
    x = df[(df.m >= lo) & (df.m <= hi)].copy()
    x['rel'] = x.lp - x.groupby('bm').apply(lambda g: np.average(g.lp, weights=g.w), include_groups=False).reindex(x.bm).to_numpy()
    return x.groupby('master').apply(lambda g: pd.Series(dict(rel=np.average(g.rel, weights=g.w), w=g.w.sum())), include_groups=False)
p1 = period(D[D.N >= 1], '2025-01', '2025-06'); p2 = period(D[D.N >= 1], '2026-05', '2026-10')
r_start = pd.Series(cs[:, idx[mi('2024-12')]] / np.where(cn[:, idx[mi('2024-12')]] > 0, cn[:, idx[mi('2024-12')]], np.nan), index=masters)
r_end = pd.Series(cs[:, idx[mi('2026-04')]] / np.where(cn[:, idx[mi('2026-04')]] > 0, cn[:, idx[mi('2026-04')]], np.nan), index=masters)
n_start = pd.Series(cn[:, idx[mi('2024-12')]], index=masters)
ev = p1.join(p2, lsuffix='1', rsuffix='2', how='inner')
ev['dr'] = (r_end - r_start).reindex(ev.index); ev['n0'] = n_start.reindex(ev.index)
ev = ev[(ev.n0 >= 10) & ev.dr.notna()]
ev['grp'] = pd.cut(ev.dr, [-9, -0.1, -0.03, 0.03, 0.1, 9], labels=['caiu ≥0,10', 'caiu 0,03–0,10', 'estável (±0,03)', 'subiu 0,03–0,10', 'subiu ≥0,10'])
ev['dp'] = ev.rel2 - ev.rel1
out['antes_depois'] = [dict(grp=str(g), n=int(len(x)), dr=float(x.dr.mean()), dp=float(np.exp(np.average(x.dp, weights=x.w1 + x.w2)) - 1))
                       for g, x in ev.groupby('grp', observed=True)]
out['antes_depois_slope'] = float(np.polyfit(ev.dr, ev.dp, 1, w=np.sqrt(ev.w1 + ev.w2))[0])
out['antes_depois_n'] = int(len(ev))

# ---------- B. janelas: a nota recente pesa mais?
def add_rating(df, N, S, minN):
    v = N[df.mi, df.ti]; return np.where(v >= minN, S[df.mi, df.ti] / np.where(v > 0, v, 1), np.nan)
wins = {}
for lab, (N_, S_), mn in [('Acumulada (nota exibida)', window(None), 10), ('Últimos 24 meses', window(24), 5), ('Últimos 12 meses', window(12), 5),
                          ('Últimos 6 meses', window(6), 3), ('Últimos 3 meses', window(3), 3), ('Último mês', window(1), 2),
                          ('Meia-vida 3 meses', ew(3), 2), ('Meia-vida 6 meses', ew(6), 3), ('Meia-vida 12 meses', ew(12), 5), ('Meia-vida 24 meses', ew(24), 5)]:
    base[lab] = add_rating(base, N_, S_, mn)
    wins[lab] = mn
# placebo: reviews dos próximos 3 meses
N_, S_ = lead(3); base['Próximos 3 meses (placebo)'] = np.where(N_[base.mi, base.ti + 1] >= 3, S_[base.mi, base.ti + 1] / np.where(N_[base.mi, base.ti + 1] > 0, N_[base.mi, base.ti + 1], 1), np.nan)
labs = list(wins) + ['Próximos 3 meses (placebo)']
common = base.dropna(subset=[l for l in labs if l not in ('Último mês', 'Próximos 3 meses (placebo)')]).copy()
res = []
for l in labs:
    d = common.dropna(subset=[l]).rename(columns={l: 'x'})
    e1, r21, sd1 = boot(d, ['x'], 'lp', ['bm'], B=100)
    e2, r22, sd2 = boot(d, ['x'], 'lp', ['bm', 'master'], B=100)
    res.append(dict(lab=l, n=int(len(d)), entre=e1[0], r2_entre=r21, sd_entre=sd1, mesmo=e2[0], r2_mesmo=r22, sd_mesmo=sd2,
                    p_sd_mesmo=float(np.exp(e2[0]['b'] * sd2) - 1), p_sd_entre=float(np.exp(e1[0]['b'] * sd1) - 1)))
out['janelas'] = res
# corrida: acumulada + desvio dos últimos 6 meses em relação à acumulada, juntos
d = common.copy(); d['rec'] = d['Últimos 6 meses'] - d['Acumulada (nota exibida)']
e, r2, _ = boot(d, ['Acumulada (nota exibida)', 'rec'], 'lp', ['bm', 'master'], B=100)
out['corrida_mesmo'] = dict(acum=e[0], rec6=e[1])
e, r2, _ = boot(d, ['Acumulada (nota exibida)', 'rec'], 'lp', ['bm'], B=100)
out['corrida_entre'] = dict(acum=e[0], rec6=e[1])
# defasagem: nota exibida de k meses atrás (mesmo anúncio)
lagres = []
for k in (1, 3, 6, 9):
    d = base.copy(); tt = d.ti - (k - 1)
    ok = tt >= 0; d = d[ok]; tt = tt[ok]
    v = cn[d.mi, tt]; d['x'] = np.where(v >= 10, cs[d.mi, tt] / np.where(v > 0, v, 1), np.nan); d = d.dropna(subset=['x'])
    e, r2, sd = boot(d, ['x'], 'lp', ['bm', 'master'], B=80)
    lagres.append(dict(k=k, est=e[0], n=int(len(d))))
out['defasagem'] = lagres
json.dump(out, open('robustez.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k != 'janelas'}, indent=1, default=float, ensure_ascii=False)[:4000])
for r in res: print(f"{r['lab']:28s} n={r['n']} entre {r['entre']['p01']*100:+.2f}% [{r['entre']['p01_lo']*100:+.1f},{r['entre']['p01_hi']*100:+.1f}] r2 {r['r2_entre']:.4f} | mesmo {r['mesmo']['p01']*100:+.2f}% [{r['mesmo']['p01_lo']*100:+.1f},{r['mesmo']['p01_hi']*100:+.1f}] r2 {r['r2_mesmo']:.4f} sd {r['sd_mesmo']:.3f} p/sd {r['p_sd_mesmo']*100:+.2f}%")
