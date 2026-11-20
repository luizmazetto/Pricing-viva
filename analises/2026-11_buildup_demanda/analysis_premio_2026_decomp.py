"""Decomposição da variação do prêmio de mercado jan–out/26 vs jan–out/25 com os coeficientes do modelo:
nota Airbnb (β 1,08 × %Airbnb × Δnota 12m), faixa Booking ≥ 8,0 (+9,5% se Booking ≥ 35%), Expedia (0,31 por ponto de share),
demais canais (0,41 cheio / 1,00 folga). O resto = residual (maturação, preço, mix de unidades etc.). Mesmos prédios, mesmos meses."""
import numpy as np, pandas as pd, math
src = open('analysis_canais_controle_reviews.py', encoding='utf-8').read().split("D['f8'] =")[0]
exec(src)
D['rb'] = [rb12(c, t) for c, t in zip(D.cd, D.t)]
D['rbs'] = [rb_shown(c, t) for c, t in zip(D.cd, D.t)]
OC = pd.read_csv('data/ocupacao_predio_mes.psv', sep='|')[['b', 'm', 'occ']]
D = D.merge(OC, on=['b', 'm'], how='left')
D['y'] = D.m.str[:4].astype(int); D['mo'] = D.m.str[5:7].astype(int)
D = D[D.mo <= 10]
city = {}
import openpyxl
wb = openpyxl.load_workbook('data/Inputs_Demanda_original.xlsx', read_only=True)
for row in wb['ADR Acomodação'].iter_rows(min_row=5, max_row=57, values_only=True): city.setdefault(row[1], row[0])
B_A, B_EXP, G_FULL, G_FOLGA, BAND, BAND_MIN = 1.08, 0.31, 0.41, 1.00, 0.095, 0.35
out = []
for cd, g in D.groupby('cd'):
    a, b = g[g.y == 2025], g[g.y == 2026]
    ms = sorted(set(a.mo) & set(b.mo))
    if len(ms) < 6: continue
    a, b = a[a.mo.isin(ms)], b[b.mo.isin(ms)]
    def agg(x):
        n = x.n.sum(); tot = x.rev_tot.sum()
        return dict(n=n, prem=(x.rev * x.n).sum() / (x.mrevpar * x.n).sum(), s_air=x.rev_air.sum() / tot, s_bk=x.rev_bk.sum() / tot,
                    s_exp=x.rev_exp.sum() / tot, s_out=(tot - x.rev_air.sum() - x.rev_bk.sum() - x.rev_exp.sum()) / tot,
                    ra=np.average(x.ra.dropna(), weights=x.n[x.ra.notna()]) if x.ra.notna().any() else np.nan,
                    f8=np.average((x.rbs >= 8.0).astype(float)[x.rbs.notna()], weights=x.n[x.rbs.notna()]) if x.rbs.notna().any() else np.nan,
                    occ=np.average(x.occ.dropna(), weights=x.n[x.occ.notna()]) if x.occ.notna().any() else np.nan)
    A, Bb = agg(a), agg(b)
    sh_air = (A['s_air'] + Bb['s_air']) / 2; sh_bk = (A['s_bk'] + Bb['s_bk']) / 2
    e_air = math.exp(B_A * sh_air * (Bb['ra'] - A['ra'])) - 1 if not (np.isnan(A['ra']) or np.isnan(Bb['ra'])) else 0.0
    e_band = (1 + BAND) ** (Bb['f8'] - A['f8']) - 1 if sh_bk >= BAND_MIN and not (np.isnan(A['f8']) or np.isnan(Bb['f8'])) else 0.0
    occ = np.nanmean([A['occ'], Bb['occ']]); gd = G_FULL if occ >= 0.80 else G_FOLGA
    e_exp = B_EXP * (Bb['s_exp'] - A['s_exp']); e_out = gd * (Bb['s_out'] - A['s_out'])
    real = Bb['prem'] / A['prem'] - 1
    expl = (1 + e_air) * (1 + e_band) * (1 + e_exp + e_out) - 1
    out.append(dict(cd=cd, city=city.get(cd), meses=len(ms), n=Bb['n'], wrev=(a.rev*a.n).sum(), wm25=(a.mrevpar*a.n).sum(), wm26=(b.mrevpar*b.n).sum(), wr26=(b.rev*b.n).sum(), prem25=A['prem'] - 1, prem26=Bb['prem'] - 1, real=real,
                    ra25=A['ra'], ra26=Bb['ra'], f8_25=A['f8'], f8_26=Bb['f8'], dexp=Bb['s_exp'] - A['s_exp'], dout=Bb['s_out'] - A['s_out'],
                    e_air=e_air, e_band=e_band, e_exp=e_exp, e_out=e_out, expl=expl, resid=(1 + real) / (1 + expl) - 1))
O = pd.DataFrame(out)
O.to_csv('/tmp/decomp_premio_2026.csv', index=False)  # resultado prédio a prédio fica fora do repositório
def tot(x):
    # peso = receita nossa de 2025 (média ponderada de (1+efeito) = razão de somas quando o mercado varia igual)
    w = x.wrev
    p25 = x.wrev.sum() / x.wm25.sum() - 1; p26 = x.wr26.sum() / x.wm26.sum() - 1
    r = dict(predios=len(x), prem25=p25, prem26=p26, real=(1 + p26) / (1 + p25) - 1)
    for k in ('e_air', 'e_band', 'e_exp', 'e_out', 'expl'): r[k] = np.average(x[k], weights=w)
    r['resid'] = (1 + r['real']) / (1 + r['expl']) - 1
    r['ra25'] = np.average(x.ra25.fillna(x.ra26), weights=w); r['ra26'] = np.average(x.ra26.fillna(x.ra25), weights=w)
    r['dexp'] = np.average(x.dexp, weights=w); r['dout'] = np.average(x.dout, weights=w)
    return r
pd.set_option('display.width', 220)
res = {lab: tot(O[sel]) for lab, sel in (('Portfólio', O.cd.notna()), ('SP', O.city == 'SP'), ('FLN', O.city == 'FLN'))}
print(pd.DataFrame(res).T.round(4).to_string())
print()
print(O.sort_values('n', ascending=False)[['cd', 'city', 'meses', 'prem25', 'prem26', 'real', 'ra25', 'ra26', 'f8_25', 'f8_26', 'dexp', 'dout', 'e_air', 'e_band', 'e_exp', 'e_out', 'expl', 'resid']].round(3).to_string(index=False))
