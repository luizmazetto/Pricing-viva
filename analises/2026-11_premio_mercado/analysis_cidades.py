"""Recorte por cidade e submercado. Gera cidades.json (rode depois de analysis.py)."""
import csv, collections, json, math

YTD = [f'{m:02d}' for m in range(1, 11)]
CMP = YTD + ['11p']
FWD = ['2026-12', '2027-01', '2027-02', '2027-03']

SUB = {
  'São Paulo': {
    'Jardins / Paulista': ['NXF', 'NXH', 'NXP', 'PVF', 'PVJ', 'PVP', 'NXB', 'HEG', 'MEL'],
    'Pinheiros / Vila Madalena / Perdizes': ['AYR', 'HLK', 'MOU', 'OMG', 'ONZ', 'PED', 'PQJ', 'TOF', 'SPZ', 'CNZ'],
    'Itaim / Vila Nova / Vila Olímpia': ['NUN', 'NXD', 'NXV', 'PVN', 'UPR', 'KAS'],
    'Vila Mariana / Paraíso / Moema / Santo Amaro': ['FYP', 'URB', 'EQL', 'AYM', 'HBV'],
    'Centro / Higienópolis / Consolação / Bela Vista': ['AGR', 'AYH', 'SCN', 'DGE', 'NXM'],
  },
  'Florianópolis': {
    'Ingleses (praia)': ['AGM', 'AQL', 'CAN'],
    'Centro / Agronômica / Saco Grande': ['ARB', 'TBG', 'TPV', 'ZEE', 'FST'],
  },
  'Balneário Camboriú': {'Balneário Camboriú': ['TSO']},
}

def rd(p): return list(csv.DictReader(open(p, encoding='utf-8'), delimiter='|'))
base = json.load(open('analise.json', encoding='utf-8'))
SS = set(base['meta']['SS']); FIRST = base['meta']['first_day']
code = lambda b: b.split(' ')[0]
allb = sorted(FIRST)
bycode = {code(b): b for b in allb}
sub_of = {}
for c, subs in SUB.items():
    for s, codes in subs.items():
        for k in codes: sub_of[bycode[k]] = (c, s)

mix = collections.defaultdict(dict)
for r in rd('data/mix_2026.psv'): mix[r['b']][r['cat']] = int(r['n'])
units = {b: sum(v.values()) for b, v in mix.items()}

# ---- mercado diário agregado por prédio/cat/mês/tipo de dia
M = {}
for r in rd('data/market_building_cat_month_dt.psv'):
    M[(r['b'], r['cat'], r['m'], r['dt'])] = {k: float(r[k]) for k in ('n','mbp','p25','p50','p75','occ','rp','tal')}

KEYS = ('occ','mbp','p25','p50','p75','rp','tal','dem')
def cell(b, c, m, dts):
    rows = [M.get((b, c, m, dt)) for dt in dts]
    if any(x is None for x in rows): return None
    n = sum(x['n'] for x in rows)
    out = {k: sum(x[k]*x['n'] for x in rows)/n for k in ('occ','mbp','p25','p50','p75','rp','tal')}
    out['dem'] = sum(x['occ']*x['tal']*x['n'] for x in rows)/n
    return out

def bpair(b, m, dts):
    """mercado do prédio em 2025 e 2026 no mês m (mesmas categorias nos 2 anos)"""
    acc = {y: collections.defaultdict(float) for y in 'ab'}; W = 0
    for c, w in mix.get(b, {}).items():
        x, y = cell(b, c, f'2025-{m}', dts), cell(b, c, f'2026-{m}', dts)
        if not x or not y: continue
        W += w
        for lab, d in (('a', x), ('b', y)):
            for k in KEYS: acc[lab][k] += w*d[k]
    if not W: return None
    return {lab: {k: v/W for k, v in acc[lab].items()} for lab in 'ab'}

def group(bs, months, dts=('wd','we')):
    """média ponderada por unidades dos prédios, média simples dos meses"""
    per_m = []
    for m in months:
        acc = {y: collections.defaultdict(float) for y in 'ab'}; W = 0; nb = 0
        for b in bs:
            if units.get(b, 0) < 300: continue
            g = bpair(b, m, dts)
            if not g: continue
            w = units[b]; W += w; nb += 1
            for lab in 'ab':
                for k in KEYS: acc[lab][k] += w*g[lab][k]
        if W: per_m.append((m, nb, {lab: {k: v/W for k, v in acc[lab].items()} for lab in 'ab'}))
    if not per_m: return None
    res = {lab: {k: sum(p[2][lab][k] for p in per_m)/len(per_m) for k in KEYS} for lab in 'ab'}
    res['nb'] = max(p[1] for p in per_m); res['months'] = [p[0] for p in per_m]
    return res

def rnd(x):
    if isinstance(x, dict): return {k: rnd(v) for k, v in x.items()}
    if isinstance(x, list): return [rnd(v) for v in x]
    return round(x, 4) if isinstance(x, float) else x

# ---- nosso prêmio por cidade
us = rd('data/us_building_month.psv')
for r in us:
    for k in ('n','rev','occ','mo','mbp','mrevpar'): r[k] = float(r[k])
def agg(rows):
    n = sum(r['n'] for r in rows)
    if not n: return None
    s = lambda k: sum(r[k]*r['n'] for r in rows)/n
    rev, mr, occ, mo = s('rev'), s('mrevpar'), s('occ'), s('mo')
    return dict(n=n, revpar=rev, mrevpar=mr, prem=rev/mr, occ=occ, mo=mo, adr=rev/occ if occ else None, madr=mr/mo if mo else None)
def us_sel(bs, ms): return [r for r in us if r['b'] in bs and r['m'] in ms]

out = {'cities': {}}
for c, subs in SUB.items():
    cb = [b for b in allb if sub_of.get(b, ('',))[0] == c]
    ss = [b for b in cb if b in SS]; nw = [b for b in cb if b not in SS]
    cd = {'buildings': cb, 'ss': ss, 'new': nw}
    # prêmio mensal
    serie = []
    for m in CMP:
        serie.append(dict(m=m,
            ss25=agg(us_sel(set(ss), {f'2025-{m}'})), ss26=agg(us_sel(set(ss), {f'2026-{m}'})),
            new26=agg(us_sel(set(nw), {f'2026-{m}'})), all25=agg(us_sel(set(cb), {f'2025-{m}'})), all26=agg(us_sel(set(cb), {f'2026-{m}'}))))
    cd['prem_serie'] = serie
    blocks = {'ytd': YTD, 'ago_out': ['08','09','10'], 'out': ['10'], 'nov': ['11p']}
    cd['prem'] = {k: dict(ss25=agg(us_sel(set(ss), {f'2025-{m}' for m in v})), ss26=agg(us_sel(set(ss), {f'2026-{m}' for m in v})),
                          new26=agg(us_sel(set(nw), {f'2026-{m}' for m in v})),
                          all25=agg(us_sel(set(cb), {f'2025-{m}' for m in v})), all26=agg(us_sel(set(cb), {f'2026-{m}' for m in v})))
                  for k, v in blocks.items()}
    # mercado: cidade e submercados, mês a mês e blocos, total / semana / fim de semana
    def mk(bs):
        return dict(monthly=[dict(m=m, g=group(bs, [m])) for m in CMP],
                    ytd=group(bs, YTD), ytd_wd=group(bs, YTD, ('wd',)), ytd_we=group(bs, YTD, ('we',)),
                    ago_out=group(bs, ['08','09','10']), ao_wd=group(bs, ['08','09','10'], ('wd',)), ao_we=group(bs, ['08','09','10'], ('we',)),
                    nov=group(bs, ['11p']))
    cd['mkt'] = mk(cb)
    cd['subs'] = {s: dict(codes=codes, **mk([bycode[k] for k in codes])) for s, codes in subs.items()} if len(subs) > 1 else {}
    out['cities'][c] = cd

# ---- pace futuro
F = collections.defaultdict(dict)
for r in rd('data/market_forward.psv'):
    F[(r['b'], r['m'])][r['cat']] = {k: float(r[k]) for k in ('occ','stly','ly','tal','tal_ly')}
def fwd(bs, m):
    acc = collections.defaultdict(float); W = 0
    for b in bs:
        for c, w in mix.get(b, {}).items():
            x = F.get((b, m), {}).get(c)
            if not x: continue
            W += w
            for k, v in x.items(): acc[k] += w*v
    return {k: v/W for k, v in acc.items()} if W else None
for c, cd in out['cities'].items():
    cd['fwd'] = {m: fwd(cd['buildings'], m) for m in FWD}
    cd['fwd_subs'] = {s: {m: fwd([bycode[k] for k in v['codes']], m) for m in FWD} for s, v in cd['subs'].items()}
out['SUB'] = SUB
json.dump(rnd(out), open('cidades.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok')
