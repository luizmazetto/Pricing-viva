"""Reviews (Airbnb) x prêmio de mercado. Gera reviews.json. Ver README.md."""
import json, numpy as np, pandas as pd

rng = np.random.default_rng(7)
R = pd.read_csv('data/reviews_master_month.psv', sep='|')
P = pd.read_csv('data/premio_master_month.psv', sep='|')
FIRST = {l.split('|')[0]: l.split('|')[1].strip() for l in open('../2026-11_premio_mercado/data/first_day.psv', encoding='utf-8').read().splitlines()[1:]}
CITY = json.load(open('../2026-11_premio_mercado/analise.json', encoding='utf-8'))['meta']['city']
SS = set(json.load(open('../2026-11_premio_mercado/analise.json', encoding='utf-8'))['meta']['SS'])
BLD = sorted(set(P.b))                      # prédios atuais
R = R[R.b.isin(BLD)].copy()

def mi(m): return int(m[:4]) * 12 + int(m[5:7]) - 1
def ms(i): return f'{i//12}-{i%12+1:02d}'
R['t'] = R.m.map(mi); P['t'] = P.m.map(mi)
T0, T1 = mi('2022-12'), mi('2026-10')
ALLT = range(T0, T1 + 1)

# ---------- avaliação acumulada (nota exibida) e móvel por anúncio, no fim de cada mês
cols = ['n', 'sg', 'n5', 'n3', 'scl', 'slo', 'sva', 'sac', 'sci', 'sco', 'nsub']
full = (R.groupby(['master', 't'])[cols].sum()
          .reindex(pd.MultiIndex.from_product([R.master.unique(), ALLT], names=['master', 't']), fill_value=0))
cum = full.groupby(level=0).cumsum()
r12 = full.groupby(level=0).rolling(12, min_periods=1).sum().droplevel(0)
M = pd.DataFrame({'N': cum.n, 'rat': cum.sg / cum.n.replace(0, np.nan),
                  'N12': r12.n, 'r12': r12.sg / r12.n.replace(0, np.nan)})
for k, s in (('cl', 'scl'), ('lo', 'slo'), ('va', 'sva'), ('ac', 'sac'), ('ci', 'sci'), ('co', 'sco')):
    M[k] = cum[s] / cum.nsub.replace(0, np.nan)
M = M.reset_index()
M['t'] = M.t + 1                           # nota no fim do mês t vale para o mês t+1 (sem olhar o futuro)

# ---------- painel anúncio × mês com prêmio
D = P[(P.n >= 20) & (P.mrevpar > 0)].merge(M, on=['master', 't'], how='left')
D['prem'] = D.rev / D.mrevpar
D = D[D.prem > 0].copy()
D['lp'] = np.log(D.prem); D['w'] = D.n; D['bm'] = D.b + D.m

def demean(df, x, y, fes, it=25):
    X = df[x].to_numpy(float).copy(); Y = df[y].to_numpy(float).copy(); w = df.w.to_numpy(float)
    keys = [pd.factorize(df[f])[0] for f in fes]
    for _ in range(it if len(fes) > 1 else 1):
        for k in keys:
            sw = np.bincount(k, w)
            X -= (np.bincount(k, w * X) / sw)[k]; Y -= (np.bincount(k, w * Y) / sw)[k]
    return X, Y, w

def slope(df, x, y, fes):
    X, Y, w = demean(df, x, y, fes)
    return float(np.sum(w * X * Y) / np.sum(w * X * X)), float(np.sqrt(np.sum(w * X * X) / w.sum()))

def boot(df, x, y, fes, B=200):
    b0, sd = slope(df, x, y, fes)
    groups = {g: d for g, d in df.groupby('b')}; names = list(groups)
    bs = []
    for _ in range(B):
        pick = rng.choice(names, len(names))
        dd = pd.concat([groups[n].assign(b=f'{n}#{i}', bm=groups[n].bm + f'#{i}', master=groups[n].master + f'#{i}') for i, n in enumerate(pick)])
        bs.append(slope(dd, x, y, fes)[0])
    lo, hi = np.percentile(bs, [5, 95])
    return dict(b=b0, lo=float(lo), hi=float(hi), sd_x=sd, n=int(len(df)), per01=float(np.exp(b0 * .1) - 1),
                per01_lo=float(np.exp(lo * .1) - 1), per01_hi=float(np.exp(hi * .1) - 1))

E = {}
A = D[(D.N >= 10) & D.rat.notna()]
E['entre_anuncios'] = boot(A, 'rat', 'lp', ['bm'])
E['mesmo_anuncio'] = boot(A, 'rat', 'lp', ['bm', 'master'])
A12 = D[(D.N12 >= 5) & D.r12.notna()]
E['entre_anuncios_12m'] = boot(A12, 'r12', 'lp', ['bm'])
E['mesmo_anuncio_12m'] = boot(A12, 'r12', 'lp', ['bm', 'master'])
# decomposição: ocupação relativa x diária relativa (entre anúncios, nota exibida)
A = A.assign(locc=np.log(A.occ.clip(lower=0.01) / A.mo.clip(lower=0.01)))
A = A.assign(ladr=A.lp - A.locc)
E['dec_occ'] = slope(A, 'rat', 'locc', ['bm'])[0]; E['dec_adr'] = slope(A, 'rat', 'ladr', ['bm'])[0]
# subnotas (uma de cada vez, entre anúncios)
E['sub'] = {k: slope(A[A[k].notna()], k, 'lp', ['bm'])[0] for k in ('cl', 'lo', 'va', 'ac', 'ci', 'co')}
E['sub_sd'] = {k: slope(A[A[k].notna()], k, 'lp', ['bm'])[1] for k in ('cl', 'lo', 'va', 'ac', 'ci', 'co')}
# curva por faixas (desvio da nota vs média do prédio no mês)
X, Y, w = demean(A, 'rat', 'lp', ['bm'])
bins = [-9, -.3, -.15, -.05, .05, .15, .3, 9]; labs = ['< −0,30', '−0,30 a −0,15', '−0,15 a −0,05', '±0,05', '+0,05 a +0,15', '+0,15 a +0,30', '> +0,30']
cut = np.digitize(X, bins) - 1
E['bins'] = [dict(lab=labs[i], n=int((cut == i).sum()), x=float(np.average(X[cut == i], weights=w[cut == i])),
                  dev=float(np.exp(np.average(Y[cut == i], weights=w[cut == i])) - 1)) for i in range(len(labs)) if (cut == i).sum() >= 10]


# ---------- canal: participação do Airbnb na receita e notas do Booking
CH = pd.read_csv('data/canal_master_month.psv', sep='|')
CH['t'] = CH.m.map(mi)
D = D.merge(CH[['master', 't', 'rev_airbnb', 'rev_booking', 'rev_total']], on=['master', 't'], how='left')
sh = CH[CH.m >= '2026-01'].groupby('master')[['rev_airbnb', 'rev_booking', 'rev_total']].sum()
sh['air'] = sh.rev_airbnb / sh.rev_total.replace(0, np.nan)
D = D.merge(sh[['air']], left_on='master', right_index=True, how='left')
A = A.merge(sh[['air']], left_on='master', right_index=True, how='left')
E['por_canal'] = {
    'airbnb_alto': boot(A[A.air >= 0.7], 'rat', 'lp', ['bm'], B=100),
    'airbnb_baixo': boot(A[A.air < 0.7], 'rat', 'lp', ['bm'], B=100),
}
BK = pd.read_csv('data/reviews_booking_master_month.psv', sep='|'); BK = BK[BK.b.isin(BLD)].copy(); BK['t'] = BK.m.map(mi)
bf = BK.groupby(['master', 't'])[['n', 'sg']].sum().reindex(pd.MultiIndex.from_product([BK.master.unique(), ALLT], names=['master', 't']), fill_value=0)
bc = bf.groupby(level=0).cumsum().reset_index(); bc['t'] = bc.t + 1
bc = bc.rename(columns={'n': 'Nb', 'sg': 'Sb'}); bc['bk'] = bc.Sb / bc.Nb.replace(0, np.nan)
A = A.merge(bc[['master', 't', 'Nb', 'bk']], on=['master', 't'], how='left')
AB = A[(A.Nb >= 10) & A.bk.notna()]
E['booking'] = boot(AB, 'bk', 'lp', ['bm'], B=100)          # por +1 ponto (escala 0–10)
E['booking']['sd_x'] = slope(AB, 'bk', 'lp', ['bm'])[1]

# ---------- modelo conjunto dos dois canais, com interação pelo peso do canal no anúncio
def ols_fe(df, xs, y, fes, it=25):
    w = df.w.to_numpy(float); keys = [pd.factorize(df[f])[0] for f in fes]
    Z = df[xs + [y]].to_numpy(float).copy()
    for _ in range(it if len(fes) > 1 else 1):
        for k in keys:
            sw = np.bincount(k, w)
            for j in range(Z.shape[1]): Z[:, j] -= (np.bincount(k, w * Z[:, j]) / sw)[k]
    X, Y = Z[:, :-1], Z[:, -1]
    return np.linalg.solve((X * w[:, None]).T @ X, (X * w[:, None]).T @ Y)

def boot_ols(df, xs, y, fes, B=150):
    b0 = ols_fe(df, xs, y, fes); groups = {g: d for g, d in df.groupby('b')}; names = list(groups); bs = []
    for _ in range(B):
        pick = rng.choice(names, len(names))
        dd = pd.concat([groups[n].assign(b=f'{n}#{i}', bm=groups[n].bm + f'#{i}', master=groups[n].master + f'#{i}') for i, n in enumerate(pick)])
        bs.append(ols_fe(dd, xs, y, fes))
    bs = np.array(bs)
    return dict(zip(xs, [dict(b=float(b0[j]), lo=float(np.percentile(bs[:, j], 5)), hi=float(np.percentile(bs[:, j], 95))) for j in range(len(xs))]))

J = A.merge(sh[['rev_airbnb', 'rev_booking', 'rev_total']].assign(bks=lambda d: d.rev_booking / d.rev_total.replace(0, np.nan)), left_on='master', right_index=True, how='left')
J = J[(J.N >= 10) & (J.Nb >= 10) & J.bk.notna() & J.air.notna() & J.bks.notna()].copy()
AIR0, BK0 = 0.45, 0.35                        # pesos de referência (≈ média do portfólio em 2026)
J['ra_c'] = J.rat - J.rat.mean(); J['rb_c'] = (J.bk - J.bk.mean()) / 2      # Booking em "estrelas" (0–10 ÷ 2)
J['ra_x'] = J.ra_c * (J.air - AIR0); J['rb_x'] = J.rb_c * (J.bks - BK0)
xs = ['ra_c', 'rb_c', 'ra_x', 'rb_x']
E['conjunto'] = {y: boot_ols(J, xs, y, ['bm']) for y in ('lp', 'locc', 'ladr')}
E['conjunto_n'] = int(len(J)); E['ref_pesos'] = [AIR0, BK0]
# prêmio de cada canal (receita do canal por noite disponível ÷ RevPAR mercado) contra a nota do próprio canal
D2 = D.merge(bc[['master', 't', 'Nb', 'bk']], on=['master', 't'], how='left')
D2['pa'] = D2.rev_airbnb / D2.n / D2.mrevpar; D2['pb'] = D2.rev_booking / D2.n / D2.mrevpar
CA = D2[(D2.N >= 10) & D2.rat.notna() & D2.pa.notna()]
CB = D2[(D2.Nb >= 10) & D2.bk.notna() & D2.pb.notna()].assign(bk5=lambda d: d.bk / 2)
E['canal_proprio'] = dict(airbnb=boot(CA, 'rat', 'pa', ['bm'], B=100), booking=boot(CB, 'bk5', 'pb', ['bm'], B=100),
                          cruz_air_bk=slope(CB[CB.rat.notna() & (CB.N >= 10)], 'rat', 'pb', ['bm'])[0],
                          cruz_bk_air=slope(CA[CA.bk.notna() & (CA.Nb >= 10)].assign(bk5=lambda d: d.bk / 2), 'bk5', 'pa', ['bm'])[0])
# ao longo do tempo, mesmo anúncio, cada canal (nota exibida acumulada)
E['tempo_airbnb'] = boot(D2[(D2.N >= 10) & D2.rat.notna()], 'rat', 'lp', ['bm', 'master'], B=100)
E['tempo_booking'] = boot(D2[(D2.Nb >= 10) & D2.bk.notna()].assign(bk5=lambda d: d.bk / 2), 'bk5', 'lp', ['bm', 'master'], B=100)

ch_b = CH[CH.m >= '2026-01'].groupby('b')[['rev_airbnb', 'rev_booking', 'rev_total']].sum()
BKb = BK.groupby('b')[['n', 'sg']].sum(); BK26 = BK[BK.m.between('2026-01', '2026-10')].groupby('b')[['n', 'sg']].sum()
BK25 = BK[BK.m.between('2025-01', '2025-10')].groupby('b')[['n', 'sg']].sum()

# ---------- nível prédio: evolução mensal
Rb = R.groupby(['b', 't'])[cols].sum().reset_index()
Mb = D.assign(rw=D.rat * D.w, cw=D.rat.notna() * D.w).groupby(['b', 't']).agg(rw=('rw', 'sum'), cw=('cw', 'sum'),
        rev=('rev', lambda s: float((s * D.loc[s.index, 'w']).sum())), mr=('mrevpar', lambda s: float((s * D.loc[s.index, 'w']).sum())), w=('w', 'sum')).reset_index()
Mb['rat_exib'] = Mb.rw / Mb.cw.replace(0, np.nan); Mb['prem'] = Mb.rev / Mb.mr
bld = {}
for b in BLD:
    rr = Rb[Rb.b == b].set_index('t')[cols].reindex(ALLT, fill_value=0)
    roll = rr[['n', 'sg', 'n5', 'n3']].rolling(12, min_periods=1).sum()
    q = rr[['n', 'sg', 'n5']].rolling(3, min_periods=1).sum()
    mb = Mb[Mb.b == b].set_index('t')
    ser = []
    for t in range(mi('2024-01'), T1 + 1):
        ser.append(dict(m=ms(t), n=int(rr.n[t]), avg=float(rr.sg[t] / rr.n[t]) if rr.n[t] else None,
                        r12=float(roll.sg[t] / roll.n[t]) if roll.n[t] >= 10 else None, n12=int(roll.n[t]),
                        p5_12=float(roll.n5[t] / roll.n[t]) if roll.n[t] >= 10 else None,
                        r3=float(q.sg[t] / q.n[t]) if q.n[t] >= 5 else None,
                        exib=float(mb.rat_exib[t]) if t in mb.index and pd.notna(mb.rat_exib[t]) else None,
                        prem=float(mb.prem[t]) if t in mb.index else None))
    tot = R[R.b == b]
    bld[b] = dict(city=CITY.get(b, ''), first=FIRST.get(b), ss=b in SS, serie=ser,
                  n_total=int(tot.n.sum()), life=float(tot.sg.sum() / tot.n.sum()) if tot.n.sum() else None)

# prêmio por prédio jan–out 25 e 26 (mesma base do relatório de prêmio)
def bprem(b, y):
    d = P[(P.b == b) & P.m.between(f'{y}-01', f'{y}-10')]
    return float((d.rev * d.n).sum() / (d.mrevpar * d.n).sum()) if len(d) and (d.mrevpar * d.n).sum() > 0 else None
def ryear(b, y, lo='01', hi='10'):
    d = R[(R.b == b) & R.m.between(f'{y}-{lo}', f'{y}-{hi}')]
    return (float(d.sg.sum() / d.n.sum()), int(d.n.sum()), float(d.n5.sum() / d.n.sum())) if d.n.sum() >= 10 else (None, int(d.n.sum()), None)
for b, x in bld.items():
    x['prem25'], x['prem26'] = bprem(b, 2025), bprem(b, 2026)
    x['rev24'], x['rev25'], x['rev26'] = ryear(b, 2024, '01', '12'), ryear(b, 2025), ryear(b, 2026)
    s = {r['m']: r for r in x['serie']}
    x['exib_oct25'] = s['2025-10']['exib']; x['exib_oct26'] = s['2026-10']['exib']
    if b in ch_b.index and ch_b.rev_total[b] > 0:
        x['air_share'] = float(ch_b.rev_airbnb[b] / ch_b.rev_total[b]); x['bk_share'] = float(ch_b.rev_booking[b] / ch_b.rev_total[b])
    x['bk25'] = float(BK25.sg[b] / BK25.n[b]) if b in BK25.index and BK25.n[b] >= 10 else None
    x['bk26'] = float(BK26.sg[b] / BK26.n[b]) if b in BK26.index and BK26.n[b] >= 10 else None
    x['bk_n26'] = int(BK26.n[b]) if b in BK26.index else 0
    x['r12_oct25'] = s['2025-10']['r12']; x['r12_oct26'] = s['2026-10']['r12']; x['n12_oct26'] = s['2026-10']['n12']

# painel prédio × mês: prêmio vs nota exibida (FE prédio + mês)
PB = Mb[Mb.rat_exib.notna() & (Mb.prem > 0)].assign(lp=lambda d: np.log(d.prem), m=lambda d: d.t.map(ms))
PB = PB.assign(w=PB.w, bm=PB.b, master=PB.b)
E['predio_tempo'] = boot(PB, 'rat_exib', 'lp', ['b', 'm'])

# variação same store: Δ prêmio jan–out vs Δ nota (12m até out)
pts = []
for b, x in bld.items():
    if x['ss'] and x['prem25'] and x['prem26'] and x['r12_oct25'] and x['r12_oct26']:
        pts.append(dict(b=b, city=x['city'], dp=x['prem26'] - x['prem25'], dr=x['r12_oct26'] - x['r12_oct25'],
                        de=(x['exib_oct26'] or 0) - (x['exib_oct25'] or 0), u=float(P[(P.b == b) & (P.m >= '2026-01')].n.sum() / 304)))
dp = np.array([p['dp'] for p in pts]); dr = np.array([p['dr'] for p in pts]); de = np.array([p['de'] for p in pts])
E['ss_corr_r12'] = float(np.corrcoef(dr, dp)[0, 1]); E['ss_corr_exib'] = float(np.corrcoef(de, dp)[0, 1])
E['ss_slope_r12'] = float(np.polyfit(dr, dp, 1)[0])

# cenário inercial: nota exibida em out/27 se os próximos 12 meses repetirem os últimos 12 (volume e nota)
el_lo, el_hi = E['mesmo_anuncio']['b'], E['entre_anuncios']['b']
scen = []
for b, x in bld.items():
    if not x['exib_oct26'] or not x['r12_oct26']: continue
    d = D[(D.b == b) & (D.m == '2026-10') & D.N.notna()]
    Ncum = float(np.average(d.N, weights=d.w)) if len(d) else None
    n12m = float(np.average(d.N12, weights=d.w)) if len(d) else None
    if not Ncum: continue
    proj = (x['exib_oct26'] * Ncum + x['r12_oct26'] * n12m) / (Ncum + n12m)
    dr_ = proj - x['exib_oct26']
    scen.append(dict(b=b, city=x['city'], exib=x['exib_oct26'], r12=x['r12_oct26'], Ncum=Ncum, n12=n12m, proj=proj, d=dr_,
                     prem=x['prem26'], imp_lo=float(np.exp(el_lo * dr_) - 1), imp_hi=float(np.exp(el_hi * dr_) - 1),
                     up01_lo=float(np.exp(el_lo * .1) - 1), up01_hi=float(np.exp(el_hi * .1) - 1)))

out = dict(E=E, bld=bld, ss_pts=pts, scen=scen, meta=dict(n_reviews=int(R.n.sum()), n_masters=int(R.master.nunique()), panel=int(len(D))))
json.dump(out, open('reviews.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
print(json.dumps(E, indent=1, default=float)[:3000])
