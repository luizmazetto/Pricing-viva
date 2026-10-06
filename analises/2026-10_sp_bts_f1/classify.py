"""Classifica prédios de SP para BTS (30-31/out) e F1 (5-7/nov) e gera recomendacoes.json.
Fonte: views.listing_daily_stats (BigQuery, base do dashboard 58 Us vs Market), extraída em 2026-10-06."""
import csv, json, os
D = os.path.join(os.path.dirname(__file__), 'data')

def rows(name):
    with open(os.path.join(D, name), encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='|'))

num = lambda v: float(v) if v not in ('', None) else None
ly = {r['building']: r for r in rows('f1_ly_same_store.psv')}
rel = {r['building']: {k: num(v) for k, v in r.items() if k != 'building'} for r in rows('bts_relative_base.psv')}

def short(b):
    return b.split(' - ', 1)[0].strip()

out = {'BTS': [], 'F1': []}
for r in rows('building_events.psv'):
    x = {k: (num(v) if k not in ('ev', 'building') else v) for k, v in r.items()}
    occ, mo, ask, p50, p75, p90 = x['occ'], x['mkt_occ'], x['ask_unsold'], x['mkt_p50'], x['mkt_p75'], x['mkt_p90']
    pi = occ / mo if mo else None
    x['pi'] = pi
    x['ask_vs_p50'] = ask / p50 - 1
    x['code'] = short(x['building'])
    x['remaining'] = round(x['unit_nights'] * (1 - occ))
    if x['ev'] == 'BTS':
        b = rel.get(x['building'])
        if b:
            base_pi = b['base_st_T28'] / (b['base_mkt_T28'] / 100)
            now_pi = b['bts_st_T28'] / (b['bts_mkt_T28'] / 100)
            thin = b['base_st_T28'] * b['base_nights'] < 10
        else:  # prédio sem base histórica de T-28: usa a posição de hoje vs índice médio da cidade
            base_pi, now_pi, thin = 0.39, pi, True
            b = {'bts_st_T24': None, 'base_st_T24': None, 'bts_mkt_T28': 1, 'base_mkt_T28': 1}
        ri = now_pi / base_pi if base_pi and not thin else None
        x.update(base_pi=base_pi, now_pi=now_pi, ri=ri, thin=thin,
                 own_lift=b['bts_st_T24'] / b['base_st_T24'] if b['base_st_T24'] and b['bts_st_T24'] is not None else None,
                 mkt_lift=b['bts_mkt_T28'] / b['base_mkt_T28'])
        r_ = ri if ri is not None else pi / 0.39  # sem base própria: usa o índice médio da cidade (0,39)
        rtxt = f'Índice relativo {r_:.2f}: no T-28 temos {now_pi:.2f} do mercado, e o normal deste prédio é {base_pi:.2f}.' if ri is not None else f'Base histórica curta; comparado ao índice médio da cidade (0,39), o relativo é {r_:.2f}.'
        if occ >= 0.5:
            act, tag = 'Proteger e subir', 'up'
            tgt = max(ask * 1.15, p75)
            why = f'Já vendeu {occ:.0%} das noites. {rtxt} Suba o que sobrou para no mínimo o p75 (R$ {p75:.0f}).'
        elif r_ >= 1.2 and ask > p75 and occ < 0.35:
            act, tag = 'Acima do normal: manter', 'hold'; tgt = ask
            why = f'{rtxt} Vende melhor que o seu padrão, mas o pedido já está acima do p75 (R$ {p75:.0f}) e só {occ:.0%} está vendido. Mantenha o preço, sem subir.'
        elif r_ >= 1.2:
            act, tag = 'Acima do normal: subir', 'up'
            tgt = min(ask * 1.10, max(ask, p90))
            why = f'{rtxt} Está vendendo melhor que o seu padrão. Suba 10% o que sobrou.'
        elif r_ >= 0.8:
            if ask > p90:
                act, tag = 'No normal, mas acima do p90', 'down'; tgt = p90
                why = f'{rtxt} Ritmo normal, mas o pedido está acima do p90 (R$ {p90:.0f}). Traga para o p90.'
            else:
                act, tag = 'Manter', 'hold'; tgt = ask
                why = f'{rtxt} Ritmo dentro do padrão do prédio.'
        elif ask > p75 * 1.05:
            act, tag = 'Esticado: reduzir', 'down'
            tgt = max(p75 if r_ >= 0.5 else (p50 + p75) / 2, ask * (0.75 if r_ >= 0.5 else 0.65))
            why = f'{rtxt} Abaixo do padrão, com pedido acima do p75 (R$ {p75:.0f}).'
        elif ask >= p50:
            act, tag = 'Ajustar e revisar setup', 'down'
            tgt = ask * (0.95 if r_ >= 0.5 else 0.9)
            why = f'{rtxt} Abaixo do padrão com preço entre o p50 e o p75. Corte {5 if r_ >= 0.5 else 10}% e confira estadia mínima, restrições e distribuição.'
        else:
            act, tag = 'Não é preço: revisar setup', 'check'
            tgt = ask
            why = f'{rtxt} O preço já está abaixo do p50 (R$ {p50:.0f}). Antes de baixar mais, confira estadia mínima, bloqueios, canais e conteúdo.'
    else:
        l = ly.get(x['building'])
        x['ly'] = {k: num(v) for k, v in l.items() if k != 'building'} if l else None
        behind_ly = bool(l) and num(l['occ_now_2026']) is not None and num(l['occ_now_2026']) < num(l['occ_T33_2025'])
        x['behind_ly'] = behind_ly
        if occ >= 0.18 or (pi >= 0.75 and occ >= 0.15):
            act, tag = 'Vendeu à frente: proteger', 'up'
            tgt = max(ask * 1.15, min(p75, ask * 1.35))
            why = f'Já está em {occ:.0%} de ocupação, 30 dias antes. No ano passado a cidade estava em 7% nesse ponto. Suba o que sobrou e considere estadia mínima de 3 noites.'
        elif ask < p50 * 0.95 and not behind_ly and occ > 0.05:
            act, tag = 'Abaixo do mercado: subir', 'up'
            ref = x['ly']['adr_final_2025'] if l else 0
            tgt = min(max(p50, ref or 0), ask * 1.25)
            why = f'Pedido R$ {ask:.0f} está abaixo do p50 do mercado (R$ {p50:.0f}).' + (f' ADR final da F1 2025 foi R$ {ref:.0f}.' if ref else '')
        elif ask > p90:
            act, tag = 'Acima do p90: aparar', 'down'
            tgt = p90
            why = f'Pedido R$ {ask:.0f} acima do p90 do mercado (R$ {p90:.0f}), com {occ:.0%} vendido. Traga para o p90, sem ir abaixo do p75.'
        elif behind_ly:
            act, tag = 'Manter (atrás de 2025)', 'hold'
            tgt = ask
            why = f'Ocupação de {occ:.0%} contra {x["ly"]["occ_T33_2025"]:.0%} no mesmo ponto de 2025 (ADR final 2025: R$ {x["ly"]["adr_final_2025"]:.0f}). Não suba agora. Se continuar atrás no T-14, reduza até 10%.'
        else:
            act, tag = 'Manter e segurar', 'hold'
            tgt = ask
            why = 'Preço dentro da faixa p50 a p90 do mercado. Em 2025 a demanda chegou tarde, então não dê desconto antes do checkpoint de T-14.'
    x.update(action=act, tag=tag, target=round(tgt), delta=tgt / ask - 1 if ask else 0, why=why)
    out[x['ev']].append(x)

for ev in out:
    out[ev].sort(key=lambda x: (['up', 'down', 'check', 'hold'].index(x['tag']), -x['unit_nights']))
json.dump(out, open(os.path.join(os.path.dirname(__file__), 'recomendacoes.json'), 'w'), ensure_ascii=False, indent=1)
for ev in out:
    print(ev)
    for x in out[ev]:
        print(f"  {x['code']:5} {x['action']:28} ri {x.get('ri') or 0:.2f} occ {x['occ']:.2f} mo {x['mkt_occ']:.2f} pi {x['pi']:.2f} ask {x['ask_unsold']:.0f} p50 {x['mkt_p50']:.0f} p75 {x['mkt_p75']:.0f} -> {x['target']} ({x['delta']:+.0%}) rem {x['remaining']}")
    tot = sum(x['unit_nights'] for x in out[ev]); occn = sum(x['unit_nights']*x['occ'] for x in out[ev]); mo = sum(x['unit_nights']*x['mkt_occ'] for x in out[ev])
    print(f"  TOTAL nights {tot:.0f} occ {occn/tot:.3f} mkt {mo/tot:.3f}")
