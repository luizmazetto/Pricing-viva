"""Gera analise.json a partir dos .psv em data/ (ver README.md)."""
import csv, collections, json, math

MES = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
YTD = [f'{m:02d}' for m in range(1, 11)]          # jan-out (meses fechados)
CMP = YTD + ['11p']                                # + nov 1-17

def rd(p): return list(csv.DictReader(open(p, encoding='utf-8'), delimiter='|'))

# ---------------- nosso lado (listing_daily_stats, fórmula do dashboard 58) ----------------
us = rd('data/us_building_month.psv')
for r in us:
    for k in ('n','rev','occ','mo','mbp','mrevpar','occ_mt'): r[k] = float(r[k])
city = {r['b']: r['city'] for r in us}
first = {}
for r in sorted(us, key=lambda r: r['m']): first.setdefault(r['b'], r['m'])
# primeiro dia de operação (para o ramp-up), extraído da mesma base
FIRST_DAY = {l.split('|')[0]: l.split('|')[1].strip() for l in open('data/first_day.psv', encoding='utf-8').read().splitlines()[1:]}
SS = sorted(b for b in city if FIRST_DAY[b] < '2025-01-01')

def agg(rows):
    n = sum(r['n'] for r in rows)
    if n == 0: return None
    s = lambda k: sum(r[k]*r['n'] for r in rows)/n
    rev, mr, occ, mo = s('rev'), s('mrevpar'), s('occ'), s('mo')
    return dict(n=n, revpar=rev, mrevpar=mr, prem=rev/mr if mr else None, occ=occ, mo=mo,
                adr=rev/occ if occ else None, madr=mr/mo if mo else None, mt=s('occ_mt'))

def sel(bs, months):
    return [r for r in us if r['b'] in bs and r['m'] in months]

def yoy(bs, mm):
    a = agg(sel(bs, {f'2025-{m}' for m in mm})); b = agg(sel(bs, {f'2026-{m}' for m in mm}))
    return a, b

out = {}
ALL = set(city)
NEW = sorted(b for b in city if b not in SS)

# série mensal do prêmio: todos, same store, novos
serie = []
for y in ('2025','2026'):
    for m in CMP:
        k = f'{y}-{m}'
        row = {'m': k}
        for lab, bs in (('all', ALL), ('ss', set(SS)), ('new', set(NEW))):
            a = agg(sel(bs, {k}))
            row[lab] = a and {kk: (round(v, 4) if isinstance(v, float) else v) for kk, v in a.items()}
        serie.append(row)
out['serie'] = serie

# same store: YTD e trimestres
def pack(a):
    return a and {k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}
blocks = {'ytd': YTD, 't1': ['01','02','03'], 't2': ['04','05','06'], 't3': ['07','08','09'], 'out': ['10'], 'nov': ['11p'], 'ago_out': ['08','09','10']}
out['ss_blocks'] = {k: [pack(x) for x in yoy(set(SS), v)] for k, v in blocks.items()}
out['all_blocks'] = {k: [pack(x) for x in yoy(ALL, v)] for k, v in blocks.items()}
out['new_ytd26'] = pack(agg(sel(set(NEW), {f'2026-{m}' for m in YTD})))

# por prédio same store
ssb = []
for b in SS:
    a, c = yoy({b}, YTD); a3, c3 = yoy({b}, ['08','09','10']); an, cn = yoy({b}, ['11p'])
    ssb.append(dict(b=b, city=city[b], u25=a['n']/304, u26=c['n']/304, y25=pack(a), y26=pack(c), r25=pack(a3), r26=pack(c3), n25=pack(an), n26=pack(cn)))
out['ss_buildings'] = ssb

# prédios novos: curva de ramp-up por mês desde a entrada
def month_index(b, m):
    fy, fm = int(FIRST_DAY[b][:4]), int(FIRST_DAY[b][5:7])
    y, mm = int(m[:4]), int(m[5:7])
    return (y-fy)*12 + (mm-fm)
ramp = []
for b in NEW:
    rows = sorted([r for r in us if r['b'] == b and not r['m'].endswith('p') and r['m'] <= '2026-10'], key=lambda r: r['m'])
    # junta nov/2025 (1-17 e 18-30) num mês só
    full = collections.defaultdict(list)
    for r in us:
        if r['b'] == b and r['m'][:7] <= '2026-10':
            full[r['m'][:7]].append(r)
    pts = []
    for m in sorted(full):
        a = agg(full[m]); i = month_index(b, m)
        if i >= 1 and a['n'] >= 60:   # M1 = primeiro mês cheio após a entrada; ignora meses com < ~2 unidades
            pts.append(dict(i=i, m=m, prem=round(a['prem'], 4), occ=round(a['occ'], 4), mo=round(a['mo'], 4),
                            adr=round(a['adr'] or 0, 2), madr=round(a['madr'] or 0, 2), u=round(a['n']/30.4, 1)))
    l3 = agg([r for m in ('2026-08','2026-09','2026-10') for r in full.get(m, [])])
    ytd = agg(sel({b}, {f'2026-{m}' for m in YTD}))
    ramp.append(dict(b=b, city=city[b], first=FIRST_DAY[b], pts=pts, l3=pack(l3), ytd26=pack(ytd)))
out['ramp'] = ramp

# ---------------- mercado (Pricelabs, nova metodologia), mix de categorias fixo de 2026 ----------------
mk = rd('data/market_building_cat_month.psv')
M = {}
for r in mk:
    f = lambda k: float(r[k]) if r[k] else None
    M[(r['b'], r['cat'], r['m'])] = dict(mbp=f('mbp'), p50=f('p50'), occ=f('occ'), rp=f('rp'), tal=f('tal'))
mix = collections.defaultdict(dict)
for r in rd('data/mix_2026.psv'): mix[r['b']][r['cat']] = int(r['n'])

def bm(b, m25, m26):
    """mercado do prédio nos dois anos, só com categorias que têm dado nos dois; None se nada."""
    acc = {y: collections.defaultdict(float) for y in ('a','b')}; W = 0
    for c, w in mix[b].items():
        x, y = M.get((b, c, m25)), M.get((b, c, m26))
        if not x or not y or None in (x['occ'], y['occ'], x['mbp'], y['mbp']): continue
        W += w
        for lab, d in (('a', x), ('b', y)):
            acc[lab]['occ'] += w*d['occ']; acc[lab]['mbp'] += w*d['mbp']; acc[lab]['rp'] += w*d['rp']
            acc[lab]['p50'] += w*(d['p50'] or d['mbp']); acc[lab]['tal'] += w*(d['tal'] or 0)
    if W == 0: return None
    return {lab: {k: v/W for k, v in acc[lab].items()} for lab in ('a','b')}

def bm_period(b, mm):
    """média dos meses com dado nos dois anos"""
    got = [(m, bm(b, f'2025-{m}', f'2026-{m}')) for m in mm]
    got = [(m, g) for m, g in got if g]
    if not got: return None
    res = {}
    for lab in ('a','b'):
        res[lab] = {k: sum(g[lab][k] for _, g in got)/len(got) for k in ('occ','mbp','rp','p50','tal')}
    res['months'] = [m for m, _ in got]
    return res

units = {b: sum(v.values()) for b, v in mix.items()}
mkt_b = []
for b in sorted(mix):
    if units[b] < 300: continue
    y = bm_period(b, YTD); r3 = bm_period(b, ['08','09','10']); nv = bm_period(b, ['11p'])
    if not y: continue
    mkt_b.append(dict(b=b, city=city.get(b, ''), ss=b in SS, months=y['months'], ytd=y, l3=r3, nov=nv))
out['mkt_buildings'] = mkt_b

def city_series(cities):
    rows = []
    for m in CMP:
        acc = {lab: collections.defaultdict(float) for lab in ('a','b')}; W = 0
        for b in mix:
            if city.get(b) not in cities or units[b] < 300: continue
            g = bm(b, f'2025-{m}', f'2026-{m}')
            if not g: continue
            w = units[b]; W += w
            for lab in ('a','b'):
                for k, v in g[lab].items(): acc[lab][k] += w*v
        if W: rows.append(dict(m=m, **{lab: {k: round(v/W, 4) for k, v in acc[lab].items()} for lab in ('a','b')}))
    return rows
out['mkt_city'] = {'São Paulo': city_series({'São Paulo'}), 'Florianópolis': city_series({'Florianópolis'}),
                   'Balneário Camboriú': city_series({'Balneário Camboriú'}),
                   'Total': city_series({'São Paulo','Florianópolis','Balneário Camboriú'})}
out['meta'] = dict(SS=SS, NEW=NEW, first_day=FIRST_DAY, city=city)
json.dump(out, open('analise.json','w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok')

# ---------------- curva média de ramp-up (mediana entre prédios novos) ----------------
EXCL = {'MEL 184 - Melo Alves', 'MOU 1508 - Mourato Coelho', 'PED 832 - Pedroso de Moraes', 'EQL 130 - Equalize Vila Mariana', 'NXM 118 - Next Mackenzie'}
by_i = collections.defaultdict(list)
for r in out['ramp']:
    if r['b'] in EXCL: continue
    for p in r['pts']:
        if p['i'] <= 12: by_i[p['i']].append(p['prem'])
def med(v):
    v = sorted(v); n = len(v)
    return v[n//2] if n % 2 else (v[n//2-1]+v[n//2])/2
out['ramp_median'] = [dict(i=i, med=round(med(v), 4), n=len(v)) for i, v in sorted(by_i.items())]
for r in out['ramp']:
    def avg_i(lo, hi):
        v = [p['prem'] for p in r['pts'] if lo <= p['i'] <= hi]
        return round(sum(v)/len(v), 4) if v else None
    r['m1_3'] = avg_i(1, 3); r['m4_6'] = avg_i(4, 6); r['m7_12'] = avg_i(7, 12)
out['excl_ramp'] = sorted(EXCL)
json.dump(out, open('analise.json','w', encoding='utf-8'), ensure_ascii=False, indent=1)
