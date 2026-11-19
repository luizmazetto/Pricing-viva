"""Teste: os ganhos líquidos de Expedia / demais canais mudam quando controlamos pelas notas (Airbnb 12m, Booking 12m e faixa ≥ 8,0)?
E o efeito da nota Airbnb muda quando controlamos pelo mix de canais? Nível prédio, efeito fixo de prédio + mês, peso = noites."""
import numpy as np, pandas as pd, collections
rng = np.random.default_rng(11)
REV = '../2026-11_reviews_premio/data/'
mi = lambda m: int(m[:4]) * 12 + int(m[5:7]) - 1
D = pd.read_csv('data/historico_predio_mes.psv', sep='|')
X = pd.read_csv('data/expedia_receita_predio_mes.psv', sep='|')
D = D.merge(X, on=['b', 'm'], how='left').fillna({'rev_exp': 0})
D = D[(D.mrevpar.notna()) & (D.n >= 150) & (D.n_mkt / D.n >= 0.8)].copy()
D['w'] = D.n; D['t'] = D.m.map(mi); D['cd'] = D.b.str.split(' - ').str[0].str.strip()
den = D.n * D.mrevpar
D['p_exp'] = D.rev_exp / den; D['p_out'] = (D.rev_tot - D.rev_air - D.rev_bk - D.rev_exp) / den
D['p_ota'] = (D.rev_air + D.rev_bk) / den; D['p_tot'] = D.rev_tot / den
D['s_air'] = D.rev_air / D.rev_tot; D['s_bk'] = D.rev_bk / D.rev_tot
D['s_exp'] = D.rev_exp / D.rev_tot; D['s_out'] = 1 - D.s_air - D.s_bk - D.s_exp

def monthly(p):
    R = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
    for r in pd.read_csv(p, sep='|').itertuples():
        x = R[r.b.split(' - ')[0].strip()][mi(r.m)]; x[0] += r.n; x[1] += r.sg
    return R
RA, RB = monthly(REV + 'reviews_master_month.psv'), monthly(REV + 'reviews_booking_master_month.psv')
def win(R, c, t, a, b):            # meses t-b+1 .. t-a
    n = s = 0.0
    for j in range(t - b + 1, t - a + 1):
        x = R[c].get(j)
        if x: n += x[0]; s += x[1]
    return n, s
def ra12(c, t):
    n, s = win(RA, c, t - 1, 0, 12); return s / n if n >= 3 else np.nan   # até o mês anterior
def rb12(c, t):
    n, s = win(RB, c, t - 1, 0, 12); return s / n if n >= 3 else np.nan
def rb_shown(c, t):
    num = dd = 0.0
    for j, wj in enumerate((0.85, 0.10, 0.05)):
        n, s = win(RB, c, t - 1, 12 * j, 12 * (j + 1))
        if n: num += wj * s / n; dd += wj
    return num / dd if dd and sum(win(RB, c, t - 1, 0, 36)[0:1]) >= 10 else np.nan
D['ra'] = [ra12(c, t) for c, t in zip(D.cd, D.t)]
D['rb'] = [rb12(c, t) for c, t in zip(D.cd, D.t)]
D['rbs'] = [rb_shown(c, t) for c, t in zip(D.cd, D.t)]
D['f8'] = (D.rbs >= 8.0).astype(float)
# termo da fórmula: peso médio do Airbnb no prédio (fixo) × nota 12m até o mês anterior
D['air_b'] = D.groupby('b').rev_air.transform('sum') / D.groupby('b').rev_tot.transform('sum')
D['bk_b'] = D.groupby('b').rev_bk.transform('sum') / D.groupby('b').rev_tot.transform('sum')
D['xa'] = D.air_b * D.ra
D['xb'] = D.bk_b * D.rb
D['f8s'] = D.f8 * (D.bk_b >= 0.35)

def fe(df, xs, y, fes=('b', 'm'), it=30):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in fes]; Z = df[xs + [y]].to_numpy(float).copy()
    for _ in range(it):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(Z.shape[1]): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    X_, Y = Z[:, :-1], Z[:, -1]
    return np.linalg.lstsq((X_ * w[:, None]).T @ X_, (X_ * w[:, None]).T @ Y, rcond=None)[0]
def boot(df, xs, y, B=300):
    b0 = fe(df, xs, y); G = {g: d for g, d in df.groupby('b')}; nm = list(G); bs = []
    for _ in range(B):
        pick = rng.choice(nm, len(nm)); bs.append(fe(pd.concat([G[k].assign(b=f'{k}#{i}') for i, k in enumerate(pick)]), xs, y))
    bs = np.array(bs)
    return {x: (round(b0[j], 3), round(np.percentile(bs[:, j], 5), 3), round(np.percentile(bs[:, j], 95), 3)) for j, x in enumerate(xs)}

S = D.dropna(subset=['ra', 'rb', 'rbs']).copy()
print(f'amostra com notas: {S.b.nunique()} prédios, {len(S)} prédio×mês (de {D.b.nunique()} / {len(D)})')
print('correlação (dentro do prédio, sem média do prédio) entre notas e canais:')
W = S[['p_exp', 'p_out', 'ra', 'rb', 'f8']].copy()
W = W - S.groupby('b')[['p_exp', 'p_out', 'ra', 'rb', 'f8']].transform('mean')
print(W.corr().round(2).loc[['p_exp', 'p_out'], ['ra', 'rb', 'f8']].to_string())

OC = pd.read_csv('data/ocupacao_predio_mes.psv', sep='|')[['b', 'm', 'occ']]
S = S.merge(OC, on=['b', 'm'], how='left'); S['occ_b'] = S.groupby('b').occ.transform('mean')
CTRL = ['ra', 'rb', 'f8']
print('\n== 1. Ganho líquido por ponto (y = pontos totais): sem vs com controle das notas')
for lab, d in (('todos', S), ('cheios (≥80%)', S[S.occ_b >= 0.8]), ('com folga (<80%)', S[S.occ_b < 0.8])):
    a = boot(d, ['p_exp', 'p_out'], 'p_tot'); b = boot(d, ['p_exp', 'p_out'] + CTRL, 'p_tot')
    print(f'  {lab:17s} {d.b.nunique():2d} prédios | sem: Expedia {a["p_exp"]} demais {a["p_out"]}')
    print(f'  {"":17s}             | com: Expedia {b["p_exp"]} demais {b["p_out"]} | nota Airbnb {b["ra"]} Booking {b["rb"]} faixa8 {b["f8"]}')
a = boot(S, ['p_exp', 'p_out'], 'p_ota'); b = boot(S, ['p_exp', 'p_out'] + CTRL, 'p_ota')
print(f'  Airbnb+Booking por ponto | sem: Expedia {a["p_exp"]} demais {a["p_out"]} | com: Expedia {b["p_exp"]} demais {b["p_out"]}')

print('\n== 2. Efeito da nota Airbnb (y = log prêmio total, termo %Airbnb × nota 12m): sem vs com controle do mix de canais')
S['lp'] = np.log(S.p_tot)
a = boot(S, ['xa'], 'lp'); b = boot(S, ['xa', 's_exp', 's_out'], 'lp'); c = boot(S, ['xa', 's_exp', 's_out', 'xb', 'f8s'], 'lp')
print(f'  sem controle: {a["xa"]}\n  + share Expedia e demais: {b["xa"]} (Expedia {b["s_exp"]}, demais {b["s_out"]})\n  + Booking (nota e faixa): {c["xa"]} (faixa ≥8 com Booking ≥35%: {c["f8s"]})')
