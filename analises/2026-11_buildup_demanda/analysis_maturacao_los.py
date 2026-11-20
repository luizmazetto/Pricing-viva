"""Maturação e LOS × prêmio de mercado (nível prédio).
1. Maturação: prêmio (nosso RevPAR ÷ RevPAR de mercado) por idade do prédio (meses desde a abertura), com efeito fixo de prédio e
   de mês do ano (o prêmio já desconta o mercado do mês; mês do ano pega a sazonalidade). Com e sem controle de notas e canais.
2. LOS: noites ÷ reservas (Report DB, ago–set/26 ajustados) × prêmio, ADR relativo e ocupação, com efeito fixo de prédio e de mês.
Intervalos de 90% por bootstrap de prédios. Saída: só estatísticas agregadas."""
import numpy as np, pandas as pd, collections
rng = np.random.default_rng(5)
mi = lambda m: int(m[:4]) * 12 + int(m[5:7]) - 1
code = lambda b: b.split(' - ')[0].strip()

D = pd.read_csv('data/historico_predio_mes.psv', sep='|')
X = pd.read_csv('data/expedia_receita_predio_mes.psv', sep='|')
D = D.merge(X, on=['b', 'm'], how='left').fillna({'rev_exp': 0})
D = D[(D.mrevpar.notna()) & (D.n >= 150) & (D.n_mkt / D.n >= 0.8) & (D.m <= '2026-10')].copy()
D['cd'] = D.b.map(code); D['t'] = D.m.map(mi); D['moy'] = D.m.str[5:7]
D['lp'] = np.log(D.rev / D.mrevpar)
D['s_air'] = D.rev_air / D.rev_tot; D['s_exp'] = D.rev_exp / D.rev_tot; D['s_out'] = 1 - (D.rev_air + D.rev_bk + D.rev_exp) / D.rev_tot
OC = pd.read_csv('data/ocupacao_predio_mes.psv', sep='|')[['b', 'm', 'occ']]
D = D.merge(OC, on=['b', 'm'], how='left')
FD = {code(l.split('|')[0]): l.split('|')[1].strip() for l in open('../2026-11_premio_mercado/data/first_day.psv', encoding='utf-8').read().splitlines()[1:]}
D['age'] = [t - mi(FD[c][:7]) if c in FD else np.nan for c, t in zip(D.cd, D.t)]
# nota Airbnb 12m (mesma base das outras análises)
exec(open('analysis_canais_controle_reviews.py', encoding='utf-8').read().split("D = pd.read_csv('data/historico_predio_mes.psv'")[0].split('rng =')[0])
REV = '../2026-11_reviews_premio/data/'
RA = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
for r in pd.read_csv(REV + 'reviews_master_month.psv', sep='|').itertuples():
    x = RA[code(r.b)][mi(r.m)]; x[0] += r.n; x[1] += r.sg
def ra12(c, t):
    n = s = 0.0
    for j in range(t - 12, t):
        x = RA[c].get(j)
        if x: n += x[0]; s += x[1]
    return s / n if n >= 3 else np.nan
D['ra'] = [ra12(c, t) for c, t in zip(D.cd, D.t)]
D['air_b'] = D.groupby('b').rev_air.transform('sum') / D.groupby('b').rev_tot.transform('sum')
D['xa'] = D.air_b * D.ra
D['w'] = D.n

# LOS da Report DB (soma dos contratos do prédio), com os ajustes de ago–set/26
R = pd.read_csv('data/report_db_predio_mes.psv', sep='|')
for x in pd.read_csv('data/report_db_reservas_ajuste.psv', sep='|').itertuples():
    R.loc[(R.b == x.b) & (R.ctr == x.ctr) & (R.m == x.m), 'res'] = x.res_aj
for x in pd.read_csv('data/report_db_ago26_ajuste.psv', sep='|').itertuples():
    R.loc[(R.b == x.b) & (R.ctr == x.ctr) & (R.m == x.m), 'dia'] = x.dia_aj
L = R.groupby(['b', 'm'])[['dia', 'res']].sum().reset_index().rename(columns={'b': 'cd'})
L = L[(L.res >= 10)]; L['los'] = L.dia / L.res
D = D.merge(L[['cd', 'm', 'los']], on=['cd', 'm'], how='left')

def fe(df, xs, y, fes):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in fes]; Z = df[xs + [y]].to_numpy(float).copy()
    for _ in range(40):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(Z.shape[1]): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    Xm, Y = Z[:, :-1], Z[:, -1]
    return np.linalg.lstsq((Xm * w[:, None]).T @ Xm, (Xm * w[:, None]).T @ Y, rcond=None)[0]
def boot(df, xs, y, fes, B=300):
    b0 = fe(df, xs, y, fes); G = {g: d for g, d in df.groupby('cd')}; nm = list(G); bs = []
    for _ in range(B):
        pick = rng.choice(nm, len(nm)); bs.append(fe(pd.concat([G[k].assign(cd=f'{k}#{i}', b=f'{k}#{i}') for i, k in enumerate(pick)]), xs, y, fes))
    bs = np.array(bs)
    return {x: (b0[j], np.percentile(bs[:, j], 5), np.percentile(bs[:, j], 95)) for j, x in enumerate(xs)}
pc = lambda v: f'{np.expm1(v) * 100:+.1f}%'
fmt = lambda t: f'{pc(t[0])} ({pc(t[1])} a {pc(t[2])})'

print('== 1. Maturação')
M = D[D.age.notna() & (D.age >= 0)].copy()
bins = [(-1, 2, '0–2'), (2, 5, '3–5'), (5, 8, '6–8'), (8, 11, '9–11'), (11, 17, '12–17'), (17, 23, '18–23'), (23, 999, '24+')]
for lo, hi, lab in bins: M['a_' + lab] = ((M.age > lo) & (M.age <= hi)).astype(float)
cols = ['a_' + b[2] for b in bins[:-1]]          # referência: 24+ meses
print('prédios', M.cd.nunique(), 'prédio×mês', len(M), '| prédios com idade < 24m em algum mês:', M[M.age < 24].cd.nunique())
print('obs por faixa:', {b[2]: int(M['a_' + b[2]].sum()) for b in bins})
r1 = boot(M, cols, 'lp', ['cd', 'moy'])
Mc = M.dropna(subset=['xa'])
r2 = boot(Mc, cols + ['xa', 's_exp', 's_out'], 'lp', ['cd', 'moy'])
print('prêmio vs prédio maduro (24+ meses) · sem controles | com nota Airbnb e canais')
for c in cols: print(f'  {c[2:]:>6} meses: {fmt(r1[c])}  |  {fmt(r2[c])}')
# ocupação por idade
Mo = M.dropna(subset=['occ']).copy(); Mo['lo'] = np.log(Mo.occ)
r3 = boot(Mo, cols, 'lo', ['cd', 'moy'])
print('ocupação vs maduro:', {c[2:]: fmt(r3[c]) for c in cols})

print('\n== 2. LOS')
S = D.dropna(subset=['los', 'occ']).copy()
S = S[S.cd != 'HLK 407']
S['ll'] = np.log(S.los); S['lo'] = np.log(S.occ); S['ladr'] = S.lp - S.lo     # ADR relativo ao RevPAR de mercado
print('prédios', S.cd.nunique(), 'prédio×mês', len(S), '| LOS médio', round(np.average(S.los, weights=S.w), 2))
for lab, xs in (('só LOS', ['ll']), ('LOS + canais', ['ll', 's_exp', 's_out'])):
    for y, ylab in (('lp', 'prêmio (RevPAR)'), ('ladr', 'diária relativa'), ('lo', 'ocupação')):
        r = boot(S, xs, y, ['cd', 't'])
        e = r['ll']
        print(f'  {lab:14s} {ylab:16s} +10% de LOS: {pc(e[0] * np.log(1.1))} ({pc(e[1] * np.log(1.1))} a {pc(e[2] * np.log(1.1))})')
sd = (S.ll - S.groupby('cd').ll.transform('mean')).std()
print('variação típica do LOS dentro do prédio (desvio-padrão do log):', round(sd, 3))

print('\n== 3. Modelo conjunto: maturação + LOS + nota Airbnb + faixa Booking + canais (prédio + mês do ano)')
RB = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
for r in pd.read_csv(REV + 'reviews_booking_master_month.psv', sep='|').itertuples():
    x = RB[code(r.b)][mi(r.m)]; x[0] += r.n; x[1] += r.sg
def rb_shown(c, t):
    num = dd = 0.0; tot = 0.0
    for j, wj in enumerate((0.85, 0.10, 0.05)):
        n = s = 0.0
        for q in range(t - 12 * (j + 1), t - 12 * j):
            x = RB[c].get(q)
            if x: n += x[0]; s += x[1]
        tot += n
        if n: num += wj * s / n; dd += wj
    return num / dd if dd and tot >= 10 else np.nan
D['rbs'] = [rb_shown(c, t) for c, t in zip(D.cd, D.t)]
D['bk_b'] = D.groupby('b').rev_bk.transform('sum') / D.groupby('b').rev_tot.transform('sum')
D['f8s'] = ((D.rbs >= 8.0) & (D.bk_b >= 0.35)).astype(float)
D['occ_b'] = D.groupby('cd').occ.transform('mean')
D['s_out_full'] = D.s_out * (D.occ_b >= 0.8); D['s_out_folga'] = D.s_out * (D.occ_b < 0.8)
J = D[D.age.notna() & (D.age >= 0) & D.xa.notna() & D.rbs.notna() & D.los.notna() & D.occ.notna() & (D.cd != 'HLK 407')].copy()
for lo, hi, lab in bins: J['a_' + lab] = ((J.age > lo) & (J.age <= hi)).astype(float)
J['ll'] = np.log(J.los); J['lo'] = np.log(J.occ); J['ladr'] = J.lp - J.lo
XS = cols + ['ll', 'xa', 'f8s', 's_exp', 's_out_full', 's_out_folga']
print('prédios', J.cd.nunique(), 'prédio×mês', len(J))
for y, ylab in (('lp', 'PRÊMIO (RevPAR)'), ('ladr', 'DIÁRIA relativa'), ('lo', 'OCUPAÇÃO')):
    r = boot(J, XS, y, ['cd', 'moy'])
    print(' ', ylab)
    for c in cols: print(f'     idade {c[2:]:>6} meses: {fmt(r[c])}')
    e = r['ll']; print(f'     +10% LOS: {pc(e[0]*np.log(1.1))} ({pc(e[1]*np.log(1.1))} a {pc(e[2]*np.log(1.1))})')
    e = r['xa']; print(f'     nota Airbnb (β por estrela × %Airbnb): {e[0]:.2f} ({e[1]:.2f} a {e[2]:.2f})')
    e = r['f8s']; print(f'     faixa Booking ≥ 8,0 (Booking ≥ 35%): {fmt(e)}')
    for k in ('s_exp', 's_out_full', 's_out_folga'):
        e = r[k]; print(f'     {k} (log por ponto de share): {e[0]:.2f} ({e[1]:.2f} a {e[2]:.2f})')
