"""Natal (noites 21-27/dez) e Réveillon (28/dez-3/jan) 2026 em SP e FLN: pace vs 2024/2025, posição de mercado e recomendação por prédio.

Fontes (extraídas em 06/out/2026):
- data/pickup_city.psv e data/building_history.psv: tabela Calendar (VivaAnalytics), sem mid-term (estadia >= 28 noites).
  pace_06out = ocupação com reservas criadas até 06/out do ano da temporada.
- data/market_bq.psv: views.listing_daily_stats (BigQuery, base do dashboard 58). ADR, preço pedido e mercado na mesma base.
"""
import csv, json, os
H = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(H, 'data')
num = lambda v: float(v) if v not in ('', None) else None

def rows(name):
    with open(os.path.join(D, name), encoding='utf-8') as f:
        return list(csv.DictReader(f, delimiter='|'))

hist, mkt = {}, {}
for r in rows('building_history.psv'):
    hist[(r['city'], r['building'], r['period'], int(r['season']))] = {k: num(v) for k, v in r.items() if k not in ('city', 'building', 'period', 'season')}
for r in rows('market_bq.psv'):
    mkt[(r['city'], r['building'], r['period'], int(r['season']))] = {k: num(v) for k, v in r.items() if k not in ('city', 'building', 'period', 'season')}

# ---------- curvas da cidade ----------
ORDER = ['a_ate_06out', 'b_61+', 'c_31-60', 'd_15-30', 'e_8-14', 'f_0-7']
LABELS = ['06/out', 'T-60', 'T-30', 'T-14', 'T-7', 'Final']
cur = {}
for r in rows('pickup_city.psv'):
    cur.setdefault((r['city'], r['period'], int(r['season'])), {})[r['bucket']] = (int(r['nights']), num(r['adr']))
curves = {}
for (c, p, s), b in cur.items():
    st = sum(v[0] for k, v in b.items() if k != 'midterm')
    cum, pts, adrs = 0, [], []
    for o in ORDER:
        n, a = b.get(o, (0, None)); cum += n; pts.append(cum / st); adrs.append(a)
    sold = sum(b.get(o, (0, 0))[0] for o in ORDER)
    rev = sum(b[o][0] * b[o][1] for o in ORDER if o in b and b[o][1])
    curves.setdefault(f'{c}-{p}', {})[s] = dict(cum=pts, adr=adrs, st=st, final=sold / st, adr_avg=rev / sold if sold else None,
                                                  revpar=rev / st, last7_share=b.get('f_0-7', (0, 0))[0] / st,
                                                  last7_adr=b.get('f_0-7', (0, None))[1],
                                                  early_adr=(sum(b[o][0] * b[o][1] for o in ORDER[1:3] if o in b) / max(1, sum(b[o][0] for o in ORDER[1:3] if o in b))) if s < 2026 else None)

# ---------- prédios ----------
CITY_LY_PACE = {('SP', 'NAT'): curves['SP-NAT'][2025]['cum'][0], ('SP', 'REV'): curves['SP-REV'][2025]['cum'][0]}
buildings = {}
for (c, b, p, s) in sorted({k for k in hist if k[3] == 2026}):
    h26 = hist[(c, b, p, 2026)]; h25 = hist.get((c, b, p, 2025)); h24 = hist.get((c, b, p, 2024))
    m26 = mkt.get((c, b, p, 2026)); m25 = mkt.get((c, b, p, 2025))
    if not m26 or h26['st_nights'] < 20:
        continue
    pace = h26['pace_06out']
    ask, p50, p75, p90 = m26['ask'], m26['mkt_p50'], m26['mkt_p75'], m26['mkt_p90']
    ly_adr = m25['adr'] if m25 else None           # ADR 2025 na mesma base do preço pedido (listing_daily_stats)
    ly_mkt_med = m25['mkt_median_booked'] if m25 else None
    ly_final = h25['final_occ'] if h25 else None
    ly_last7 = h25['share_last7d'] / h25['final_occ'] if h25 and h25['final_occ'] else None
    ly_disc = (h25['adr_last7d'] / h25['adr_early_30plus'] - 1) if h25 and h25['adr_last7d'] and h25['adr_early_30plus'] else None
    if c == 'FLN':
        prev = [h['pace_06out'] for h in (h24, h25) if h]
        ref_year = '2024–25' if len(prev) == 2 else ('2025' if h25 else 'cidade 2024–25')
        ref = sum(prev) / len(prev) if prev else (curves[f'FLN-{p}'][2024]['cum'][0] + curves[f'FLN-{p}'][2025]['cum'][0]) / 2
    else:
        ref_year = 2025 if h25 else None
        ref = h25['pace_06out'] if h25 else CITY_LY_PACE[(c, p)]
    gap = pace - ref if ref is not None else None
    premium_ly = ask / ly_adr - 1 if ly_adr and ask else None
    x = dict(city=c, building=b, code=b.split(' - ')[0].strip(), name=' - '.join(b.split(' - ')[1:]).strip(), period=p,
             st_nights=h26['st_nights'], pace=pace, pace25=h25['pace_06out'] if h25 else None, pace24=h24['pace_06out'] if h24 else None,
             final25=ly_final, final24=h24['final_occ'] if h24 else None, ref_year=ref_year, gap=gap,
             occ=m26['occ'], mkt_occ=m26['mkt_occ'], ask=ask, p50=p50, p75=p75, p90=p90, adr_onbooks=m26['adr'],
             ly_adr=ly_adr, ly_mkt_med=ly_mkt_med, ly_mkt_occ=m25['mkt_occ'] if m25 else None, ly_occ_bq=m25['occ'] if m25 else None,
             ly_last7=ly_last7, ly_disc=ly_disc, premium_ly=premium_ly, remaining=round(h26['st_nights'] * (1 - pace)))
    tgt, tag = ask, 'hold'
    if c == 'FLN':
        ahead = gap >= 0.08 or (m26['occ'] >= 1.5 * m26['mkt_occ'] and m26['occ'] >= 0.15)
        behind = gap <= -0.05 and m26['occ'] < m26['mkt_occ']
        if ahead and ask < p75:
            act, tag = 'À frente e barato: subir', 'up'
            tgt = max(ask * 1.10, min(p75, ask * 1.15))
            why = f'Já vendeu {pace:.0%} (média de {ref_year} na mesma data: {ref:.0%}; mercado hoje: {m26["mkt_occ"]:.0%}), e o pedido (R$ {ask:.0f}) está abaixo do p75 do mercado (R$ {p75:.0f}).'
        elif ahead:
            act, tag = 'À frente: subir por degraus', 'up'
            tgt = ask * 1.05
            why = f'Já vendeu {pace:.0%} (média de {ref_year}: {ref:.0%}). O pedido já está acima do p75: suba 5% a cada semana em que o ritmo se mantiver.'
        elif premium_ly is not None and premium_ly > 0.3 and (ly_last7 or 0) >= 0.3:
            act, tag = 'Risco de repetir 2025: ajustar já', 'down'
            tgt = max(min(p75, ly_adr * 1.25), ask * 0.8)
            why = f'O pedido (R$ {ask:.0f}) está {premium_ly:.0%} acima do ADR de 2025 (R$ {ly_adr:.0f}), e em 2025 {ly_last7:.0%} das vendas vieram na última semana' + (f', com desconto de {-ly_disc:.0%}' if ly_disc and ly_disc < 0 else '') + '. Traga o preço agora para vender antes.'
        elif behind and ask > p75:
            act, tag = 'Atrás e caro: ajustar já', 'down'
            tgt = max(p75, ask * 0.8)
            why = f'{pace:.0%} vendido (média de {ref_year}: {ref:.0%}; mercado hoje: {m26["mkt_occ"]:.0%}), com o pedido acima do p75 (R$ {p75:.0f}).'
        elif behind:
            act, tag = 'Atrás: ajuste leve e restrições', 'down'
            tgt = ask * 0.93
            why = f'{pace:.0%} vendido (média de {ref_year}: {ref:.0%}; mercado hoje: {m26["mkt_occ"]:.0%}). Corte 5–8% e revise estadia mínima para o período.'
        else:
            act = 'No ritmo: manter'
            why = f'{pace:.0%} vendido (média de {ref_year}: {ref:.0%}; mercado hoje: {m26["mkt_occ"]:.0%}). Siga os checkpoints da curva de 2024.'
    else:  # SP
        strong = ly_final is not None and ly_final >= 0.8
        cheap_ly = ly_adr and ly_mkt_med and ly_adr <= 0.85 * ly_mkt_med
        city_ref = CITY_LY_PACE[(c, p)]
        ahead = pace >= 0.12 and pace - (h25['pace_06out'] if h25 else city_ref) >= 0.08
        if ahead and ask < p75:
            act, tag = 'À frente: subir', 'up'
            tgt = min(ask * 1.15, p75)
            why = f'Já vendeu {pace:.0%} (em 2025: {(h25["pace_06out"] if h25 else city_ref):.0%} na mesma data). Suba 10–15% o que sobrou.'
        elif strong and cheap_ly and ask < ly_mkt_med:
            act, tag = 'Demanda forte, vendido barato em 2025: subir piso', 'up'
            tgt = min(ly_mkt_med, ask * 1.25)
            why = f'Em 2025 fechou com {ly_final:.0%} de ocupação (mercado {m25["mkt_occ"]:.0%}) e ADR de R$ {ly_adr:.0f}, contra R$ {ly_mkt_med:.0f} de mediana vendida no mercado. Suba o preço mínimo para essas noites.'
        elif strong:
            act, tag = 'Demanda forte: segurar', 'hold'
            why = f'Em 2025 fechou com {ly_final:.0%}, e o pedido (R$ {ask:.0f}) já está acima do ADR de 2025 (R$ {ly_adr or 0:.0f}). Não dê desconto antes de T-14.'
        elif premium_ly is not None and premium_ly > 0.35 and ask > p50 * 1.05:
            act, tag = 'Muito acima do realizado: ajustar', 'down'
            tgt = max(ly_adr * 1.15, p50, ask * 0.75)
            why = f'O pedido (R$ {ask:.0f}) está {premium_ly:.0%} acima do ADR de 2025 (R$ {ly_adr:.0f}), num prédio que fechou com {ly_final:.0%}' + ('.' if ly_final is not None else ' (sem histórico).')
        elif ly_final is not None and ly_final < 0.55:
            act, tag = 'Demanda fraca: agir cedo', 'check'
            tgt = min(ask, p50)
            why = f'Em 2025 fechou com só {ly_final:.0%}. Mantenha o preço no p50 ou abaixo, ative descontos para 5 ou 7 noites e aceite estadias longas (mid-term) nessas semanas.'
        elif ly_final is None and ask < p50 * 0.6:
            act, tag = 'Preço muito abaixo do mercado: checar', 'check'
            tgt = ask * 1.25
            why = f'Pedido de R$ {ask:.0f} contra p50 de R$ {p50:.0f} no mercado. Confira se há regra de mid-term ou desconto travando o preço dessas noites antes de subir.'
        elif ly_final is None:
            act = 'Sem histórico: seguir o mercado'
            tag = 'up' if ask < p50 * 0.9 else ('down' if ask > p75 else 'hold')
            tgt = min(p50, ask * 1.25) if ask < p50 * 0.9 else (p75 if ask > p75 else ask)
            why = f'Sem temporada anterior. O pedido (R$ {ask:.0f}) está ' + ('abaixo do p50' if ask < p50 * 0.9 else ('acima do p75' if ask > p75 else 'entre o p50 e o p75')) + ' do mercado.'
        else:
            act = 'Demanda tardia normal: manter'
            why = f'Em 2025 fechou com {ly_final:.0%}, com {ly_last7 or 0:.0%} das vendas na última semana. Mantenha o preço perto do p50 e limite os descontos a 10% a partir de T-14.'
    x.update(action=act, tag=tag, target=round(tgt), delta=tgt / ask - 1 if ask else 0, why=why)
    buildings.setdefault(f'{c}-{p}', []).append(x)

for k in buildings:
    buildings[k].sort(key=lambda x: (['up', 'down', 'check', 'hold'].index(x['tag']), -x['st_nights']))
json.dump({'curves': curves, 'buildings': buildings, 'labels': LABELS}, open(os.path.join(H, 'natal_reveillon.json'), 'w'), ensure_ascii=False, indent=1, default=str)

if __name__ == '__main__':
    for k, v in curves.items():
        for s in sorted(v):
            z = v[s]; print(k, s, ' '.join(f'{c:.0%}' for c in z['cum']), f"ADR {z['adr_avg'] or 0:.0f} RevPAR {z['revpar']:.0f} last7 {z['last7_share']:.0%}@{z['last7_adr'] or 0:.0f} early {z['early_adr'] or 0:.0f}")
    for k, v in buildings.items():
        print('\n' + k)
        for x in v:
            print(f"  {x['code']:5} {x['action'][:42]:42} pace {x['pace']:.2f} ref {x['gap'] if x['gap'] is None else round(x['gap'],2)} ask {x['ask']:.0f} p50 {x['p50']:.0f} p75 {x['p75']:.0f} lyADR {x['ly_adr'] or 0:.0f} lyfin {x['final25'] or 0:.2f} -> {x['target']} ({x['delta']:+.0%})")
