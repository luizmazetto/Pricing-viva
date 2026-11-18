"""Outros canais: demanda nova ou canibalização do OTA? Prêmio por canal (RevPAR do canal ÷ RevPAR de mercado), prédio contra ele mesmo ao longo do tempo (efeito fixo de prédio e mês)."""
import numpy as np, pandas as pd
rng=np.random.default_rng(3)
D=pd.read_csv('data/historico_predio_mes.psv',sep='|')
D=D[(D.mrevpar.notna())&(D.n>=150)&(D.n_mkt/D.n>=0.8)].copy()
D['w']=D.n
D['p_air']=D.rev_air/D.n/D.mrevpar; D['p_bk']=D.rev_bk/D.n/D.mrevpar
D['p_out']=(D.rev_tot-D.rev_air-D.rev_bk)/D.n/D.mrevpar; D['p_ota']=D.p_air+D.p_bk
D['p_tot']=D.rev_tot/D.n/D.mrevpar
D['s_out']=(D.rev_tot-D.rev_air-D.rev_bk)/D.rev_tot
def fe(df,xs,y,fes=('b','m'),it=30):
    w=df.w.to_numpy(float); keys=[pd.factorize(df[f])[0] for f in fes]; Z=df[xs+[y]].to_numpy(float).copy()
    for _ in range(it):
        for k in keys:
            sw=np.bincount(k,w)
            for j in range(Z.shape[1]): Z[:,j]-=(np.bincount(k,w*Z[:,j])/sw)[k]
    X,Y=Z[:,:-1],Z[:,-1]
    return np.linalg.lstsq((X*w[:,None]).T@X,(X*w[:,None]).T@Y,rcond=None)[0]
def boot(df,xs,y,B=400):
    b0=fe(df,xs,y); G={g:d for g,d in df.groupby('b')}; nm=list(G); bs=[]
    for _ in range(B):
        pick=rng.choice(nm,len(nm)); dd=pd.concat([G[k].assign(b=f'{k}#{i}') for i,k in enumerate(pick)]); bs.append(fe(dd,xs,y))
    bs=np.array(bs); return [(round(b0[j],3),round(np.percentile(bs[:,j],5),3),round(np.percentile(bs[:,j],95),3)) for j in range(len(xs))]
print('n',len(D),'prédios',D.b.nunique())
print('OTA (air+bk) vs outros:', boot(D,['p_out'],'p_ota'))
print('  Airbnb vs outros:', boot(D,['p_out'],'p_air'), ' Booking vs outros:', boot(D,['p_out'],'p_bk'))
print('total vs outros (=1+θ):', boot(D,['p_out'],'p_tot'))
# por cidade
for c,pre in (('SP',None),):
    pass
# defasagem: outros no mês anterior
D=D.sort_values(['b','m']); D['p_out_l1']=D.groupby('b').p_out.shift(1)
d=D.dropna(subset=['p_out_l1']); print('OTA vs outros (mês anterior):', boot(d,['p_out_l1'],'p_ota',B=200))
# share outros médio e variação por prédio
s=D.groupby('b').apply(lambda g: pd.Series(dict(s_out=np.average(g.s_out,weights=g.w), p_out=np.average(g.p_out,weights=g.w))), include_groups=False)
print(s.describe().round(3))
O=pd.read_csv('data/outros_canais_predio_mes.psv',sep='|')
E=D.merge(O,on=['b','m'])
E['p_out_mt']=E.out_mt/E.n/E.mrevpar; E['p_out_st']=E.out_st/E.n/E.mrevpar
print('\nOTA vs outros mid-term e curta estadia:', boot(E,['p_out_mt','p_out_st'],'p_ota'))
print('total vs (mid-term, curta):', boot(E,['p_out_mt','p_out_st'],'p_tot'))
print('peso médio no prêmio: mid-term', round(np.average(E.p_out_mt,weights=E.w),3),'curta', round(np.average(E.p_out_st,weights=E.w),3), 'OTA', round(np.average(E.p_ota,weights=E.w),3))
# por cidade (SP vs FLN), outros total
city={}
import csv
for r in csv.DictReader(open('../2026-11_premio_mercado/data/us_building_month.psv'),delimiter='|'): city[r['b']]=r['city']
D['city']=D.b.map(city)
for c in ('São Paulo','Florianópolis'):
    print(c, 'OTA vs outros', boot(D[D.city==c],['p_out'],'p_ota',B=200))
OC=pd.read_csv('data/ocupacao_predio_mes.psv',sep='|')[['b','m','occ']]
F=D.merge(OC,on=['b','m'])
# ocupação "normal" do prédio: média do próprio prédio no período (evita usar a ocupação do mês, que é resultado)
F['occ_b']=F.groupby('b').occ.transform(lambda s: s.mean())
for lab,sel in (('prédios com ocupação média ≥ 80%',F.occ_b>=0.80),('prédios com ocupação média < 80%',F.occ_b<0.80)):
    d=F[sel]; print(lab, d.b.nunique(),'prédios | OTA vs outros', boot(d,['p_out'],'p_ota',B=300), '| total', boot(d,['p_out'],'p_tot',B=300))
