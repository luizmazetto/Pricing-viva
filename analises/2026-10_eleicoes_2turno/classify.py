"""Fim de semana do 2º turno (noites de sex 23 e sáb 24/out/2026): prédios com ocupação baixa para incentivar.

Fonte: tabela Calendar (VivaAnalytics, Metabase database 6), extraída em 13/out/2026 (T-10 para 23/out, T-11 para 24/out).
Ocupação sempre sem mid-term (estadias >= 28 noites saem do numerador e do denominador); bloqueio e manutenção não contam.
- data/now_23_24.psv: situação atual das noites 23-24/out, noite de 25/out e fechamento do 1º turno (2-3/out).
- data/base_weekends.psv: sextas e sábados de 01/ago a 03/out/2026; pace_t10 = ocupação com reservas criadas até T-10 (sex) / T-11 (sáb).
- data/city_weekends.psv: série por cidade (inclui o 2º turno de 2024 em SP).
"""
import csv, json, os
H = os.path.dirname(os.path.abspath(__file__))
num = lambda v: float(v) if v not in ('', None) else None

def rows(name):
    with open(os.path.join(H, 'data', name), encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='|'))

base = {(r['city'], r['building']): {k: num(v) for k, v in r.items() if k not in ('city', 'building')} for r in rows('base_weekends.psv')}

# Fator eleição por cidade: pickup de T-10 até o fim no 1º turno (2-3/out) / pickup nos fins de semana normais de 11-26/set.
cw = {}
for r in rows('city_weekends.psv'):
    cw.setdefault(r['city'], {})[r['date']] = r
def pickup(city, dates):
    xs = [num(cw[city][d]['final_or_now']) - num(cw[city][d]['pace_t10']) for d in dates]
    return sum(xs) / len(xs)
NORMAL = ['2026-09-11', '2026-09-12', '2026-09-18', '2026-09-19', '2026-09-25', '2026-09-26']
R1 = ['2026-10-02', '2026-10-03']
K = {c: pickup(c, R1) / pickup(c, NORMAL) for c in ('São Paulo', 'Florianópolis')}
K['Balneário Camboriú'] = K['Florianópolis']

out = []
for r in rows('now_23_24.psv'):
    c, b = r['city'], r['building']
    v = {k: num(x) for k, x in r.items() if k not in ('city', 'building')}
    bs = base.get((c, b))
    if c == 'Rio de Janeiro' or not v['n_st'] or (v['min_stay'] or 0) >= 28 or not bs or not bs['final']:
        continue  # prédio de teste, só mid-term (estadia mínima 90) ou sem histórico de fim de semana
    occ = v['bk_st'] / v['n_st']
    pace = bs['pace_t10']
    proj = min(1.0, occ + max(0.0, bs['final'] - pace) * K[c])
    r1 = v['bk_r1'] / v['n_r1'] if v['n_r1'] else None
    out.append(dict(
        city=c, building=b, units=int(v['units']), free_nights=int(v['free_n']),
        occ_now=occ, pace_normal=pace, gap_pp=(occ - pace) * 100,
        proj_final=proj, final_normal=bs['final'],
        occ_r1=r1, r1_vs_normal_pp=(r1 - bs['final']) * 100 if r1 is not None else None,
        booked_last7d=int(v['bk_l7']), ask=v['ask'], adr_booked=v['adr'], mkt_price=v['mkt_price'],
        ask_vs_mkt=(v['ask'] / v['mkt_price']) if v['ask'] and v['mkt_price'] else None,
        mkt_occ=v['mkt_occ'], min_stay=v['min_stay'], occ_25=v['bk25'] / v['n25'] if v['n25'] else None,
        mt_nights=int(v['bk_mt']),
    ))

def tier(x):
    # Crítico: projeção de fechamento < 50% e abaixo do ritmo normal, ou zerado com 10+ noites livres.
    if (x['proj_final'] < 0.50 and x['gap_pp'] < 0) or (x['occ_now'] == 0 and x['free_nights'] >= 10):
        return 'Crítico'
    if x['proj_final'] < 0.60 or x['gap_pp'] <= -5:
        return 'Atenção'
    if x['booked_last7d'] == 0 and x['gap_pp'] < 0 and x['free_nights'] >= 10:
        return 'Atenção'  # parado: nenhuma venda para o fim de semana nos últimos 7 dias
    return 'OK'
def action(x):
    a = []
    if x['ask_vs_mkt'] and x['ask_vs_mkt'] > 1.15:
        a.append(f"preço pedido {x['ask_vs_mkt']*100-100:.0f}% acima do mercado: baixar")
    elif x['tier'] != 'OK':
        a.append('preço já perto/abaixo do mercado: incentivo comercial (desconto de última hora, campanha, visibilidade)')
    if x['tier'] != 'OK' and (x['min_stay'] or 1) >= 1.8:
        a.append('liberar estadia mínima de 1 noite (sex ou sáb avulsos)')
    return '; '.join(a)
for x in out:
    x['tier'] = tier(x)
    x['action'] = action(x)
order = {'Crítico': 0, 'Atenção': 1, 'OK': 2}
out.sort(key=lambda x: (order[x['tier']], x['proj_final']))

json.dump(dict(k_election=K, buildings=out), open(os.path.join(H, 'eleicoes.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
pct = lambda v: '—' if v is None else f'{v*100:.0f}%'
for x in out:
    print(f"{x['tier']:8} {x['city'][:3]} {x['building'][:34]:34} un={x['units']:3} livres={x['free_nights']:3} "
          f"agora={pct(x['occ_now']):>4} normal={pct(x['pace_normal']):>4} gap={x['gap_pp']:+5.0f} proj={pct(x['proj_final']):>4} "
          f"(fecha normal {pct(x['final_normal'])}) 1ºturno={pct(x['occ_r1']):>4} ({x['r1_vs_normal_pp'] or 0:+.0f}) "
          f"l7={x['booked_last7d']:2} ask={x['ask'] or 0:.0f} mkt={x['mkt_price'] or 0:.0f} ms={x['min_stay']}")
with open(os.path.join(H, 'tabela.md'), 'w', encoding='utf-8') as f:
    f.write('| Nível | Cidade | Prédio | Unid. | Noites livres | Ocup. hoje | Normal em T-10 | Projeção | Fecha normal | 1º turno | Vendas 7d | Preço pedido | Mercado | Ação |\n')
    f.write('|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|\n')
    for x in out:
        f.write(f"| {x['tier']} | {x['city']} | {x['building']} | {x['units']} | {x['free_nights']} | {pct(x['occ_now'])} | {pct(x['pace_normal'])} | "
                f"{pct(x['proj_final'])} | {pct(x['final_normal'])} | {pct(x['occ_r1'])} | {x['booked_last7d']} | "
                f"{'—' if not x['ask'] else 'R$ %.0f' % x['ask']} | {'—' if not x['mkt_price'] else 'R$ %.0f' % x['mkt_price']} | {x['action'] or '—'} |\n")
print('K', {k: round(v, 2) for k, v in K.items()})
