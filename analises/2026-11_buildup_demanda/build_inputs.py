"""Preenche o histórico e as projeções (fórmulas) das abas de demanda do Inputs_Demanda.xlsx.
Entrada: data/Inputs_Demanda_original.xlsx + dados extraídos (ver README.md). Saída: Inputs_Demanda_buildup.xlsx"""
import csv, collections, copy
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.comments import Comment

SRC = 'data/Inputs_Demanda_original.xlsx'
OUT = 'Inputs_Demanda_buildup.xlsx'
REV = '../2026-11_reviews_premio/data/'
MKT = '../2026-11_premio_mercado/data/'

MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
K0 = 2024 * 12                                   # k = 0 -> Jan/24 (coluna F)
def col(k): return L(6 + k)                     # coluna da planilha para o mês k
def kof(m): return int(m[:4]) * 12 + int(m[5:7]) - 1 - K0
K_LAST_REAL, K_SET, K_OUT, K_NOV, K_END = 31, 32, 33, 34, 59   # Ago/26, Set/26, Out/26, Nov/26, Dez/28

# ------------------------------------------------------------------ dados por prédio × mês
def rd(p): return list(csv.DictReader(open(p, encoding='utf-8'), delimiter='|'))
code = lambda b: b.split(' - ')[0].strip()

H = collections.defaultdict(dict)                # (code) -> k -> dict
EXP = {(code(x['b']), kof(x['m'])): float(x['rev_exp']) for x in rd('data/expedia_receita_predio_mes.psv')}
for r in rd('data/historico_predio_mes.psv'):
    k = kof(r['m']); c = code(r['b'])
    n, nm = float(r['n']), float(r['n_mkt'])
    d = dict(n=n, rev=float(r['rev']), tot=float(r['rev_tot']), air=float(r['rev_air']), bk=float(r['rev_bk']), exp=EXP.get((c, k), 0.0))
    d['mrev'] = float(r['mrevpar']) if r['mrevpar'] and nm / n >= 0.8 else None
    H[c][k] = d

def rev_month(path, scale=1.0):
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))
    for r in rd(path):
        m = r['m']
        if m > '2026-10': continue
        x = out[code(r['b'])][int(m[:4]) * 12 + int(m[5:7]) - 1 - K0]
        x[0] += float(r['n']); x[1] += float(r['sg']) * scale
    return out
RA = rev_month(REV + 'reviews_master_month.psv')                 # Airbnb, nota 1–5
RB = rev_month(REV + 'reviews_booking_master_month.psv')         # Booking, já em 0–10 (general × 2)

def window(R, c, k, w):
    n = s = 0.0
    for j in range(k - w + 1, k + 1):
        x = R[c].get(j)
        if x: n += x[0]; s += x[1]
    return (s / n if n >= 3 else None), n

# mercado via Pricelabs direto (para completar a base de prédios novos)
mix = collections.defaultdict(dict)
for r in rd(MKT + 'mix_2026.psv'): mix[code(r['b'])][r['cat']] = float(r['n'])
PLc = collections.defaultdict(lambda: collections.defaultdict(lambda: [0.0, 0.0]))   # (code,k,cat) -> [n, rp*n]
for r in rd(MKT + 'market_building_cat_month.psv'):
    m = r['m'][:7]; k = int(m[:4]) * 12 + int(m[5:7]) - 1 - K0
    x = PLc[(code(r['b']), k)][r['cat']]; x[0] += float(r['n']); x[1] += float(r['rp']) * float(r['n'])
def pl_mkt(c, k):
    cats = PLc.get((c, k))
    if not cats: return None
    W = S = 0.0
    for cat, (n, s) in cats.items():
        w = mix[c].get(cat, 0)
        if n and w: W += w; S += w * s / n
    return S / W if W else None

# ------------------------------------------------------------------ planilha
wb = openpyxl.load_workbook(SRC)
DATA_SHEETS = ['RevPar Mercado', 'Prêmio de Mercado', 'Reviews Booking', 'Reviews Airbnb', '% Airbnb', '% Booking', '% outros']
ADR, OCC = wb['ADR Acomodação'], wb['Ocupação (Disponível)']
ROWS = list(range(5, 58))
ROWINFO = {r: dict(city=ADR.cell(r, 1).value, code=ADR.cell(r, 2).value, ctr=ADR.cell(r, 3).value, st=ADR.cell(r, 4).value) for r in ROWS}

ARIAL = 'Arial'
F_IN = Font(name=ARIAL, color='0000FF')            # input (azul)
F_CALC = Font(name=ARIAL, color='000000')
F_LINK = Font(name=ARIAL, color='008000')
F_B = Font(name=ARIAL, bold=True)
FILL_ACT = PatternFill('solid', fgColor='E2EFDA')   # Set–Out/26 realizado depois do fechamento
FILL_IN = PatternFill('solid', fgColor='FFF2CC')
FILL_KEY = PatternFill('solid', fgColor='FFFF00')
FILL_HEAD = PatternFill('solid', fgColor='9BC2E6')
thin = Side(style='thin', color='BFBFBF')

TITLES = {
    'RevPar Mercado': ('RevPar Mercado', 'R$ por noite disponível', '#,##0.00'),
    'Prêmio de Mercado': ('Prêmio de Mercado', '% acima do RevPAR de mercado', '0.0%'),
    'Reviews Booking': ('Reviews Booking', 'nota 0–10, média móvel 12 meses', '0.00'),
    'Reviews Airbnb': ('Reviews Airbnb', 'nota 1–5, média móvel 12 meses', '0.00'),
    '% Airbnb': ('% Airbnb', '% da receita de hospedagem', '0.0%'),
    '% Booking': ('% Booking', '% da receita de hospedagem', '0.0%'),
    '% outros': ('% outros', '% da receita de hospedagem', '0.0%'),
}
NOTES = {
    'RevPar Mercado': 'RevPAR de mercado = diária mediana fechada × ocupação do mercado (Pricelabs), média das noites disponíveis das nossas unidades. Mesma base do dashboard 58. Projeção: mesmo mês do ano anterior × (1 + variação da cidade em Premissas).',
    'Prêmio de Mercado': 'Prêmio = RevPAR de hospedagem nosso ÷ RevPAR de mercado − 1 (dashboard 58). Projeção: (1 + prêmio base) × exp(β Airbnb × %Airbnb × Δnota Airbnb 12m + β Booking × %Booking × Δnota Booking 12m) − 1.',
    'Reviews Booking': 'Média dos reviews do Booking (general × 2, escala 0–10) criados nos últimos 12 meses. Projeção: volume e nota mensal de Premissas por prédio (cenário em Premissas).',
    'Reviews Airbnb': 'Média dos reviews do Airbnb (general, 1–5) criados nos últimos 12 meses. Projeção: volume e nota mensal de Premissas por prédio (cenário em Premissas). É a nota usada na fórmula do prêmio.',
    '% Airbnb': 'Receita de hospedagem de reservas Airbnb ÷ receita de hospedagem total. Projeção: média nov/25–out/26.',
    '% Booking': 'Receita de hospedagem de reservas Booking ÷ receita de hospedagem total. Projeção: média nov/25–out/26.',
    '% outros': 'Tudo que não é Airbnb nem Booking (Expedia ~50%, Swap, Homelike, DIVID, Direct, Extensão, Yuca, Decolar, corretores, B2B). Projeção: média nov/25–out/26 + aumento de share da coluna S de Premissas por prédio (a partir de jan/27).',
}

def value_for(sheet, c, k):
    h = H.get(c, {}).get(k)
    if sheet == 'RevPar Mercado': return h['mrev'] if h else None
    if sheet == 'Prêmio de Mercado': return (h['rev'] / h['mrev'] - 1) if h and h['mrev'] else None
    if sheet in ('% Airbnb', '% Booking', '% outros'):
        if not h or h['tot'] <= 0: return None
        a, b = h['air'] / h['tot'], h['bk'] / h['tot']
        return {'% Airbnb': a, '% Booking': b, '% outros': max(0.0, 1 - a - b)}[sheet]
    if sheet == 'Reviews Airbnb': return window(RA, c, k, 12)[0]
    if sheet == 'Reviews Booking': return window(RB, c, k, 12)[0]

def active(r): return ROWINFO[r]['st'] == 'Ativo'
def had_units(r, k): return isinstance(ADR.cell(r, 6 + k).value, (int, float))

for name in DATA_SHEETS:
    ws = wb[name]; title, unit, fmt = TITLES[name]
    ws['A1'] = title; ws['A2'] = NOTES[name]; ws['A2'].font = Font(name=ARIAL, italic=True, size=9)
    ws['AL3'] = 'Set–Out/26: realizado (Metabase)'; ws['AN3'] = 'Projeção (fórmulas → Premissas)'
    ws['AN3'].font = copy.copy(ws['AL3'].font); ws['AN3'].fill = copy.copy(ws['AL3'].fill)
    for r in ROWS:
        c = ROWINFO[r]['code']
        ws.cell(r, 5).value = unit
        for k in range(0, K_OUT + 1):
            cell = ws.cell(r, 6 + k)
            if k <= K_LAST_REAL and not had_units(r, k): continue
            if k > K_LAST_REAL and not active(r): continue
            v = value_for(name, c, k)
            if v is None: continue
            cell.value = round(v, 6); cell.number_format = fmt
            if k > K_LAST_REAL: cell.fill = FILL_ACT; cell.font = copy.copy(F_IN)
        for k in range(K_NOV, K_END + 1):
            ws.cell(r, 6 + k).number_format = fmt

# ------------------------------------------------------------------ abas auxiliares (mesmo layout de linhas)
def mirror(name, title, note):
    ws = wb.create_sheet(name)
    ws['A1'] = title; ws['A1'].font = Font(name=ARIAL, bold=True, size=12)
    ws['A2'] = note; ws['A2'].font = Font(name=ARIAL, italic=True, size=9)
    for i, h in enumerate(['Cidade', 'Prédio', 'Contrato', 'Status', 'Unidade']):
        c = ws.cell(4, i + 1, h); c.font = F_B; c.fill = FILL_HEAD
    for r in ROWS:
        for j in range(1, 5): ws.cell(r, j, ADR.cell(r, j).value).font = Font(name=ARIAL)
    ws.freeze_panes = 'F5'; ws.column_dimensions['B'].width = 14; ws.column_dimensions['C'].width = 15; ws.column_dimensions['E'].width = 26
    return ws
def month_header(ws, k0=0, k1=K_END):
    for k in range(k0, k1 + 1):
        y = (K0 + k) // 12; m = (K0 + k) % 12
        c = ws.cell(4, 6 + k, f'{MESES[m]}/{str(y)[2:]}'); c.font = F_B; c.fill = FILL_HEAD; c.alignment = Alignment(horizontal='center')

AUX = {}
for canal, R, scale_note, nota_cell in (('Airbnb', RA, 'nota 1–5', "'Premissas por prédio'!$M"), ('Booking', RB, 'nota 0–10', "'Premissas por prédio'!$P")):
    q = mirror(f'Aux Qtd Reviews {canal}', f'Quantidade de reviews {canal} por mês',
               'Realizado: reviews criados no mês (Metabase, mesma base do dashboard 70). Projeção: volume mensal de "Premissas por prédio".')
    s = mirror(f'Aux Soma Notas {canal}', f'Soma das notas dos reviews {canal} por mês ({scale_note})',
               'Realizado: soma das notas dos reviews do mês. Projeção: quantidade × nota mensal assumida em Premissas.')
    for ws in (q, s): month_header(ws)
    for r in ROWS:
        cd = ROWINFO[r]['code']
        q.cell(r, 5, 'reviews no mês'); s.cell(r, 5, 'soma das notas')
        for k in range(0, K_OUT + 1):
            x = R[cd].get(k)
            if x:
                q.cell(r, 6 + k, x[0]).font = F_IN; s.cell(r, 6 + k, round(x[1], 2)).font = F_IN
        if not active(r): continue
        vol_col = 'E' if canal == 'Airbnb' else 'F'
        for k in range(K_NOV, K_END + 1):
            cl = col(k)
            q.cell(r, 6 + k, f"='Premissas por prédio'!${vol_col}{r}").font = F_LINK
            q.cell(r, 6 + k).number_format = '0.0'
            s.cell(r, 6 + k, f"='Aux Qtd Reviews {canal}'!{cl}{r}*{nota_cell}{r}").font = F_CALC
            s.cell(r, 6 + k).number_format = '0.0'
    AUX[canal] = (q, s)

# base de mercado (nov/25–out/26) para a 1ª volta da projeção, completando prédios novos
bm = mirror('Aux Base Mercado', 'Base de RevPAR de mercado (nov/25–out/26) para projetar nov/26–out/27',
            'Mês realizado quando existe. Sem operação no mês: RevPAR de mercado direto do Pricelabs (mediana dos nossos anúncios, mix de 2026); sem isso, média do prédio × sazonalidade da cidade.')
BASE_K = list(range(22, 34))                       # Nov/25 .. Out/26
for ws in (bm,):
    for i, k in enumerate(BASE_K):
        y = (K0 + k) // 12; m = (K0 + k) % 12
        c = ws.cell(4, 6 + i, f'{MESES[m]}/{str(y)[2:]}'); c.font = F_B; c.fill = FILL_HEAD
bm.cell(4, 18, 'Fonte').font = F_B
# sazonalidade por cidade (média dos prédios com dado)
city_idx = {}
for city in ('SP', 'FLN', 'BC'):
    cs = [ROWINFO[r]['code'] for r in ROWS if ROWINFO[r]['city'] == city and active(r)]
    prof = []
    for k in BASE_K:
        v = [H[c][k]['mrev'] for c in cs if H.get(c, {}).get(k) and H[c][k]['mrev']]
        prof.append(sum(v) / len(v) if v else None)
    mu = sum(p for p in prof if p) / len([p for p in prof if p])
    city_idx[city] = [p / mu for p in prof]
for r in ROWS:
    if not active(r): continue
    cd = ROWINFO[r]['code']; srcs = collections.Counter(); vals = {}
    for i, k in enumerate(BASE_K):
        h = H.get(cd, {}).get(k)
        if h and h['mrev']: vals[i] = (h['mrev'], 'real')
        else:
            p = pl_mkt(cd, k)
            if p: vals[i] = (p, 'pricelabs')
    if len(vals) < 12 and vals:
        ratio = sum(v / city_idx[ROWINFO[r]['city']][i] for i, (v, _) in vals.items()) / len(vals)
        for i in range(12):
            if i not in vals: vals[i] = (ratio * city_idx[ROWINFO[r]['city']][i], 'sazonal')
    for i, (v, sr) in vals.items():
        c = bm.cell(r, 6 + i, round(v, 4)); c.font = F_IN; c.number_format = '#,##0.00'; srcs[sr] += 1
        if sr != 'real': c.fill = FILL_ACT
    bm.cell(r, 18, ', '.join(f'{n} {s}' for s, n in srcs.items()))


# ------------------------------------------------------------------ sazonalidade do prêmio por cidade (prédios same store)
FIRST = {code(l.split('|')[0]): l.split('|')[1].strip() for l in open(MKT + 'first_day.psv', encoding='utf-8').read().splitlines()[1:]}
SZ = wb.create_sheet('Sazonalidade Prêmio')
SZ['A1'] = 'Sazonalidade do prêmio por cidade'; SZ['A1'].font = Font(name=ARIAL, bold=True, size=12)
SZ['A2'] = ('Índice = (1 + prêmio do mês) ÷ média de (1 + prêmio) em jul–out/26, nos prédios same store da cidade (operando antes de 2025), nov/25–out/26. '
            'BC: só TSO 001. Usado quando Premissas!C17 = 2: prêmio base do mês = (1 + média jul–out/26 do prédio) × índice − 1.')
SZ['A2'].font = Font(name=ARIAL, italic=True, size=9)
SZ.cell(4, 1, 'Cidade').font = F_B; SZ.cell(4, 1).fill = FILL_HEAD
for m in range(12):
    c = SZ.cell(4, 2 + m, MESES[m]); c.font = F_B; c.fill = FILL_HEAD; c.alignment = Alignment(horizontal='center')
SZ.cell(4, 14, 'Prédios usados').font = F_B
SZROW = {'SP': 5, 'FLN': 6, 'BC': 7}
for city, rr in SZROW.items():
    cs = sorted({ROWINFO[r]['code'] for r in ROWS if ROWINFO[r]['city'] == city and active(r)})
    ss = [c for c in cs if FIRST.get(c, '9') < '2025-01-01'] or cs
    onep = {}
    for k in range(22, 34):
        num = den = 0.0
        for c in ss:
            h = H.get(c, {}).get(k)
            if h and h['mrev']: num += h['rev'] * h['n']; den += h['mrev'] * h['n']
        onep[k] = num / den if den else None
    base = sum(onep[k] for k in range(30, 34)) / 4
    SZ.cell(rr, 1, city).font = Font(name=ARIAL)
    for k, v in onep.items():
        m = (K0 + k) % 12
        x = SZ.cell(rr, 2 + m, round(v / base, 4)); x.font = F_IN; x.fill = FILL_KEY; x.number_format = '0.00'
    SZ.cell(rr, 14, ', '.join(ss)).font = Font(name=ARIAL, size=9)
SZ.column_dimensions['A'].width = 10; SZ.column_dimensions['N'].width = 120

SZB = mirror('Sazonalidade Prêmio Prédio', 'Sazonalidade do prêmio por prédio (usada na projeção)',
             'Prédio com os 12 meses de nov/25–out/26 operando há 3+ meses: índice próprio = (1 + prêmio do mês) ÷ média de (1 + prêmio) em jul–out/26. Demais: índice da cidade (aba Sazonalidade Prêmio). Editável.')
for m in range(12):
    c = SZB.cell(4, 6 + m, MESES[m]); c.font = F_B; c.fill = FILL_HEAD; c.alignment = Alignment(horizontal='center')
SZB.cell(4, 18, 'Origem').font = F_B
for r in ROWS:
    if not active(r): continue
    cd = ROWINFO[r]['code']; fk = kof(FIRST[cd][:7]) if cd in FIRST else None
    ok = all(H.get(cd, {}).get(k) and H[cd][k]['mrev'] and (fk is None or k - fk >= 3) for k in range(22, 34))
    if ok:
        one = {k: H[cd][k]['rev'] / H[cd][k]['mrev'] for k in range(22, 34)}
        base = sum(one[k] for k in range(30, 34)) / 4
        idx = {(K0 + k) % 12: one[k] / base for k in one}
    for m in range(12):
        if ok:
            x = SZB.cell(r, 6 + m, round(idx[m], 4)); x.font = F_IN
        else:
            x = SZB.cell(r, 6 + m, f"='Sazonalidade Prêmio'!{L(2 + m)}{SZROW[ROWINFO[r]['city']]}"); x.font = F_LINK
        x.number_format = '0.00'; x.fill = FILL_KEY
    SZB.cell(r, 18, 'próprio' if ok else 'cidade')

# ------------------------------------------------------------------ Premissas
P = wb.create_sheet('Premissas', 1)
P.column_dimensions['A'].width = 3; P.column_dimensions['B'].width = 52
for cl in 'CDE': P.column_dimensions[cl].width = 14
P.column_dimensions['F'].width = 95
def put(cell, v, font=None, fill=None, fmt=None):
    c = P[cell]; c.value = v; c.font = font or Font(name=ARIAL)
    if fill: c.fill = fill
    if fmt: c.number_format = fmt
    return c
put('B1', 'Premissas do buildup de demanda', Font(name=ARIAL, bold=True, size=14))
put('B2', 'Células amarelas com texto azul são premissas: mude aqui e todas as abas de projeção (nov/26 a dez/28) recalculam.', Font(name=ARIAL, italic=True, size=9))
put('B4', '1. Mercado · variação do RevPAR de mercado vs mesmo mês do ano anterior', F_B)
for c, h in zip('BCDEF', ['Cidade', '2026 (nov–dez)', '2027', '2028', 'Racional']):
    put(f'{c}5', h, F_B, FILL_HEAD)
MKT_G = {'SP': (6, -0.011, 'Mesma variação de 2026: RevPAR de mercado jan–out/26 vs jan–out/25 nos nossos prédios de SP = −1,1% (relatório Prêmio de Mercado 2026).'),
         'FLN': (7, -0.05, 'Premissa do usuário: −5% (em 2026 foi −10,7% em jan–out).'),
         'BC': (8, 0.01, 'Mesma variação de 2026: +1,0% em jan–out (só TSO 001).')}
for city, (row, g, why) in MKT_G.items():
    put(f'B{row}', city)
    for c in 'CDE': put(f'{c}{row}', g, F_IN, FILL_KEY, '0.0%')
    put(f'F{row}', why)
def bk_shown(cd, k, w=(0.85, 0.10, 0.05)):
    n36 = window(RB, cd, k, 36)
    if n36[0] is None or n36[1] < 10: return None
    if k < 12: return n36[0]                      # até dez/24: média simples 36 meses
    num = den = 0.0
    for j, wj in enumerate(w):
        nn = ss = 0.0
        for t in range(k - 12 * (j + 1) + 1, k - 12 * j + 1):
            x = RB[cd].get(t)
            if x: nn += x[0]; ss += x[1]
        if nn: num += wj * ss / nn; den += wj
    return num / den if den else None

# piso de nota para a meta de portfólio (resolvido aqui; conferência em Premissas)
def vol_base(R, cd):
    ks = [k for k in range(22, 34) if H.get(cd, {}).get(k) or R[cd].get(k)]
    return (sum(R[cd][k][0] for k in ks if R[cd].get(k)) / len(ks)) if ks else 0.0
def solve_floor(R, target):
    pts = []
    for r in ROWS:
        if not active(r): continue
        cd = ROWINFO[r]['code']; v = vol_base(R, cd); b = window(R, cd, 33, 12)[0]
        if v > 0: pts.append((v, b if b is not None else target))
    V = sum(v for v, _ in pts); lo, hi = 0.0, 10.0
    for _ in range(80):
        x = (lo + hi) / 2
        if sum(v * max(b, x) for v, b in pts) / V < target: lo = x
        else: hi = x
    cur = sum(v * b for v, b in pts) / V
    return round(hi, 3), cur
FLOOR_A, CUR_A = solve_floor(RA, 4.75)
FLOOR_B, CUR_B = solve_floor(RB, 8.5)

for c, h in zip('BCF', ['2. Reviews · nota mensal dos reviews novos', 'Valor', 'Racional']):
    put(f'{c}10', h, F_B, FILL_HEAD if c != 'B' else None)
put('B11', 'Cenário: 1 = nota atual de cada prédio · 2 = meta de portfólio'); put('C11', 1, F_IN, FILL_KEY, '0')
put('F11', 'Cenário 1 (base): cada prédio continua recebendo, por mês, a nota média dos seus reviews dos últimos 12 meses. Cenário 2 (melhoria): prédios abaixo do piso passam a receber o piso; quem está acima mantém a própria nota.')
put('B12', 'Meta Airbnb: média do portfólio (ponderada pelo volume de reviews)'); put('C12', 4.75, F_IN, FILL_KEY, '0.00')
put('F12', f'Meta do usuário. Hoje o portfólio está em {CUR_A:.2f} (nota 12m até out/26, ponderada pelo volume). Também é a nota usada para prédio sem histórico.'.replace('.', ',', 1) if False else f'Meta do usuário. Hoje o portfólio está em {CUR_A:.2f}'.replace('.', ',') + ' (nota 12m até out/26, ponderada pelo volume). Também é a nota usada para prédio sem histórico.')
put('B13', 'Piso Airbnb no cenário 2'); put('C13', FLOOR_A, F_IN, FILL_KEY, '0.00')
put('F13', 'Calculado para a média do portfólio dar exatamente a meta (conferência na linha abaixo). Se mudar a meta: Dados > Teste de hipóteses > Atingir meta, definindo C14 = C12 alterando C13.')
put('B14', 'Média Airbnb resultante no cenário 2 (conferência)')
put('C14', "=SUMPRODUCT('Premissas por prédio'!$E$5:$E$57,'Premissas por prédio'!$L$5:$L$57)/SUM('Premissas por prédio'!$E$5:$E$57)", F_CALC, None, '0.000')
put('B15', 'Meta Booking: média do portfólio (0–10)'); put('C15', 8.5, F_IN, FILL_KEY, '0.00')
put('F15', f'Premissa do usuário. Hoje o portfólio está em {CUR_B:.2f}'.replace('.', ',') + '. Nota do Booking não entra no prêmio (β Booking = 0), só no acompanhamento.')
put('B16', 'Piso Booking no cenário 2'); put('C16', FLOOR_B, F_IN, FILL_KEY, '0.00')
put('B17', 'Média Booking resultante no cenário 2 (conferência)')
put('C17', "=SUMPRODUCT('Premissas por prédio'!$F$5:$F$57,'Premissas por prédio'!$O$5:$O$57)/SUM('Premissas por prédio'!$F$5:$F$57)", F_CALC, None, '0.000')
put('B18', 'Volume de reviews por mês'); put('C18', 'média nov/25–out/26')
put('F18', 'Por prédio, na aba Premissas por prédio (colunas E e F), editável.')
put('B20', '3. Prêmio de mercado', F_B)
put('B21', 'β Airbnb (por estrela × %Airbnb no GMV)'); put('C21', 0.95, F_IN, FILL_KEY, '0.00')
put('F21', 'Estimado na análise Reviews × prêmio (nível prédio, nota 12m): 0,95 (intervalo de 90%: 0,49 a 1,41). Ex.: 50% Airbnb e +0,1★ → +4,9% de prêmio.')
put('B22', 'β Booking (por ponto 0–10 × %Booking no GMV)'); put('C22', 0.0, F_IN, FILL_KEY, '0.00')
put('F22', 'Estimado −0,08 (intervalo −0,19 a +0,02), não significativo: zero por padrão.')
put('B23', 'Base do prêmio: 1 = média jul–out/26 constante · 2 = média jul–out/26 × sazonalidade da cidade'); put('C23', 2, F_IN, FILL_KEY, '0')
put('F23', '2 (padrão) = média de jul–out/26 do prédio, ajustada mês a mês pela sazonalidade do próprio prédio (quem tem 12 meses maduros) ou da cidade (aba Sazonalidade Prêmio Prédio). Em FLN o prêmio vai de ~0% no verão a ~+40% no inverno.')
put('B25', '4. Canais', F_B)
put('B26', '% Airbnb, % Booking e % outros'); put('C26', 'média nov/25–out/26, constante')
put('B28', '5. Ocupação × ADR · variação da nossa ocupação vs mesmo mês do ano anterior', F_B)
for c, h in zip('BCDEF', ['Cidade', '2026 (nov–dez)', '2027', '2028', 'Racional']):
    put(f'{c}29', h, F_B, FILL_HEAD)
OCC_G = {'SP': (30, (0.0, 0.0, 0.0), 'Nossa ocupação same store ficou estável em 2026 (82,7% → 82,6% em jan–out) mesmo com a do mercado subindo +1,2 p.p.: a oferta do comp set cresceu ~50% e a demanda nova se dividiu entre mais anúncios. Variação do mercado vai para a diária.'),
         'FLN': (31, (-0.03, -0.03, 0.0), 'Em 2026 nossa ocupação same store caiu −4,3 p.p. (~−6%) com mercado a −10,7%. Com mercado a −5%, metade disso (−3%) em nov/26–2027; 2028 sem nova queda.'),
         'BC': (32, (0.0, 0.0, 0.0), 'Ocupação estável (mercado de BC +0,1 p.p. em 2026).')}
for city, (row, gs, why) in OCC_G.items():
    put(f'B{row}', city)
    for c, g in zip('CDE', gs): put(f'{c}{row}', g, F_IN, FILL_KEY, '0.0%')
    put(f'F{row}', why)
put('B33', 'Teto de ocupação'); put('C33', 0.95, F_IN, FILL_KEY, '0.0%')
put('F33', 'Limite da ocupação projetada.')
put('B34', 'Como funciona', F_B)
lines = [
    'RevPAR de mercado(t) = mesmo mês do ano anterior × (1 + variação da cidade, item 1).',
    'Prêmio(t) = (1 + prêmio base) × sazonalidade (do prédio ou da cidade) × exp( β Airbnb × %Airbnb × [Nota Airbnb 12m(t) − nota base] + β Booking × %Booking × [Nota Booking 12m(t) − nota base] ) − 1.',
    'Nota 12m(t) (abas Reviews) = soma das notas ÷ quantidade de reviews dos últimos 12 meses: realizado até out/26 e, depois, volume mensal × nota mensal do cenário (item 2). Nota base = média jul–out/26.',
    'RevPAR nosso (Buildup RevPAR) = RevPAR de mercado × (1 + prêmio) × fator de calibração do prédio (Report DB ÷ Metabase, mai–ago/26).',
    'Ocupação (Buildup Ocupação) = ocupação do mesmo mês do ano anterior × (1 + variação da cidade, item 5), com teto. Mês do ano anterior em ramp-up (< 3 meses de operação) usa a média recente do prédio × sazonalidade da cidade (Aux Base Ocupação).',
    'Outros canais (item 6): se o share de Expedia ou dos demais canais sobe a partir de jan/27, o prêmio é multiplicado por (1 + ganho líquido × Δ) de cada um; Airbnb/Booking perdem share proporcionalmente.',
    'Booking (item 7): se a nota Booking exibida (ponderada 85/10/5) cruza 8,0 em relação a out/26, o prêmio sobe (ou cai) 7,5% nos prédios com Booking ≥ 35% da receita.',
    'ADR (Buildup ADR) = RevPAR nosso ÷ Ocupação. Assim a mudança de prêmio por reviews aparece na diária, como nos dados. As abas ADR Acomodação e Ocupação (Disponível) do BP puxam essas duas a partir de set/26.',
]
for i, t in enumerate(lines):
    put(f'B{35+i}', t, Font(name=ARIAL, size=10)); P.merge_cells(f'B{35+i}:F{35+i}')
put('B46', '6. Outros canais · demanda nova vs canibalização do OTA', F_B)
put('B47', 'Ocupação média que define prédio "cheio"'); put('C47', 0.80, F_IN, FILL_KEY, '0%')
put('F47', 'Média do prédio em nov/25–out/26 (Premissas por prédio, coluna Q).')
put('B48', 'Ganho líquido por ponto · demais outros canais · prédio cheio'); put('C48', 0.41, F_IN, FILL_KEY, '0.00')
put('F48', 'Demais outros = tudo que não é Airbnb, Booking nem Expedia (direto, Swap, B2B, mid-term, corretores). Prédios com ocupação média ≥ 80%: sobra 0,41 (intervalo 0,31 a 0,74).')
put('B49', 'Ganho líquido por ponto · demais outros canais · prédio com folga'); put('C49', 1.0, F_IN, FILL_KEY, '0.00')
put('F49', 'Estimado 1,18 (intervalo 0,57 a 1,75), limitado a 1,00: preenche noite vazia, demanda nova inteira.')
put('B50', 'Ganho líquido por ponto · Expedia (qualquer prédio)'); put('C50', 0.41, F_IN, FILL_KEY, '0.00')
put('F50', 'Estimado 0,41 (intervalo 0,21 a 0,65): cada ponto de prêmio via Expedia tira ~0,6 do Airbnb, com o prédio cheio ou com folga. Mesmo hóspede do Airbnb.')
put('B51', 'Aumento de share por prédio'); put('C51', 'colunas S (Expedia) e T (demais) de Premissas por prédio, a partir de jan/27')
put('F51', 'Prêmio × (1 + 0,41 × Δ Expedia + ganho dos demais × Δ demais). Airbnb e Booking perdem share na proporção. Padrão 0 p.p.')
put('B53', '7. Booking · faixa de nota 8,0 (filtro "Muito bom: 8 ou mais")', F_B)
put('B54', 'Corte da faixa (nota Booking exibida)'); put('C54', 8.0, F_IN, FILL_KEY, '0.0')
put('F54', 'Nota exibida reconstruída na aba Booking Nota Exibida (ponderação por ano abaixo).')
put('B55', 'Ganho de prêmio por estar acima do corte · Booking ≥ limite de peso'); put('C55', 0.075, F_IN, FILL_KEY, '0.0%')
put('F55', 'Estimado em 21 prédios com Booking ≥ 35% da receita, com a nota ponderada: +7,6% de prêmio (intervalo +1,4% a +12,7%). Acima de 8,0 a receita via Booking sobe ~0,11 ponto de prêmio e parte sai do Airbnb.')
put('B56', 'Peso mínimo do Booking na receita para o ganho'); put('C56', 0.35, F_IN, FILL_KEY, '0%')
put('B57', 'Ganho de prêmio · Booking abaixo do limite de peso'); put('C57', 0.0, F_IN, FILL_KEY, '0.0%')
put('F57', 'Estimado −5,4% (intervalo −14% a +3,7%), não significativo: zero. A faixa 9,0 não mostrou ganho.')
put('B59', 'Peso dos reviews dos últimos 12 meses'); put('C59', 0.85, F_IN, FILL_KEY, '0%')
put('F59', 'Ponderação do Booking desde jan/2025 (estudo com 100 hotéis espanhóis, 74.882 reviews): 85% / 10% / 5%. Antes disso, média simples de 36 meses.')
put('B60', 'Peso dos reviews de 13 a 24 meses'); put('C60', 0.10, F_IN, FILL_KEY, '0%')
put('B61', 'Peso dos reviews de 25 a 36 meses'); put('C61', 0.05, F_IN, FILL_KEY, '0%')
put('B58', 'Como entra'); put('C58', 'prêmio × (1 + ganho) se o prédio entra na faixa; ÷ (1 + ganho) se sai, em relação a out/26')
put('B43', 'Legenda', F_B)
put('B44', 'Azul claro = realizado (até ago/26) · Verde claro = realizado em set–out/26 (Metabase) ou base completada · Amarelo = projeção (fórmulas) · Amarelo forte com texto azul = premissa editável', Font(name=ARIAL, size=9))

B36 = mirror('Booking Nota Exibida', 'Nota Booking exibida (0–10)',
             'Regra do Booking: até dez/24, média simples dos últimos 36 meses; desde jan/25, 85% média dos últimos 12 meses + 10% dos 12 anteriores + 5% dos 12 antes desses (pesos em Premissas, item 7). Projeção pelas abas Aux de Booking (a partir de jan/24).')
month_header(B36)
for r in ROWS:
    cd = ROWINFO[r]['code']; B36.cell(r, 5, 'nota 0–10')
    for k in range(0, K_OUT + 1):
        v = bk_shown(cd, k)
        if v is not None: x = B36.cell(r, 6 + k, round(v, 4)); x.font = F_IN; x.number_format = '0.00'
    if not active(r): continue
    for k in range(K_NOV, K_END + 1):
        parts = []
        for j, wc in enumerate(('$C$59', '$C$60', '$C$61')):
            hi_, lo_ = k - 12 * j, max(0, k - 12 * (j + 1) + 1)
            S_ = f"SUM('Aux Soma Notas Booking'!{col(lo_)}{r}:{col(hi_)}{r})"; N_ = f"SUM('Aux Qtd Reviews Booking'!{col(lo_)}{r}:{col(hi_)}{r})"
            parts.append((f"Premissas!{wc}*IF({N_}>0,{S_}/{N_},0)", f"Premissas!{wc}*({N_}>0)"))
        fx = f"=IFERROR(({'+'.join(a for a, _ in parts)})/({'+'.join(b for _, b in parts)}),\"\")"
        x = B36.cell(r, 6 + k, fx); x.font = F_CALC; x.number_format = '0.00'; x.fill = FILL_IN

# ------------------------------------------------------------------ Premissas por prédio
PP = mirror('Premissas por prédio', 'Premissas por prédio', 'Calculadas a partir do realizado; podem ser sobrescritas (ex.: volume de reviews de prédio novo).')
heads = {5: 'Reviews Airbnb/mês (média nov/25–out/26)', 6: 'Reviews Booking/mês (média nov/25–out/26)', 7: 'Prêmio base (média jul–out/26)',
         8: 'Nota Airbnb 12m base (média jul–out/26)', 9: 'Nota Booking 12m base (média jul–out/26)',
         10: 'Fator de calibração RevPAR (Report DB ÷ Mercado × (1+Prêmio), mai–ago/26)',
         11: 'Nota Airbnb atual (12m até out/26)', 12: 'Nota Airbnb no cenário meta (máx. entre atual e piso)', 13: 'Nota Airbnb mensal usada na projeção',
         14: 'Nota Booking atual (12m até out/26)', 15: 'Nota Booking no cenário meta', 16: 'Nota Booking mensal usada na projeção',
         17: 'Ocupação média (nov/25–out/26)', 18: 'Ganho líquido por ponto · demais outros canais', 19: 'Δ share Expedia a partir de jan/27 (p.p.)',
         20: 'Δ share demais outros a partir de jan/27 (p.p.)', 21: 'Share Expedia atual (média nov/25–out/26)', 22: 'Share demais outros atual (média nov/25–out/26)',
         23: 'Nota Booking exibida em out/26', 24: 'Acima do corte em out/26 (1 = sim)'}
for c, h in heads.items():
    x = PP.cell(4, c, h); x.font = F_B; x.fill = FILL_HEAD; x.alignment = Alignment(wrap_text=True, vertical='top'); PP.column_dimensions[L(c)].width = 20
PP.row_dimensions[4].height = 78
for r in ROWS:
    PP.cell(r, 5).value = None
    if not active(r): continue
    f = {
        5: (f"=IFERROR(AVERAGE('Aux Qtd Reviews Airbnb'!AC{r}:AM{r}),0)", '0.0'),
        6: (f"=IFERROR(AVERAGE('Aux Qtd Reviews Booking'!AC{r}:AM{r}),0)", '0.0'),
        7: (f"=IFERROR(AVERAGE('Prêmio de Mercado'!AJ{r}:AM{r}),\"\")", '0.0%'),
        8: (f"=IFERROR(AVERAGE('Reviews Airbnb'!AJ{r}:AM{r}),\"\")", '0.00'),
        9: (f"=IFERROR(AVERAGE('Reviews Booking'!AJ{r}:AM{r}),\"\")", '0.00'),
        11: (f"=IF(ISNUMBER('Reviews Airbnb'!AM{r}),'Reviews Airbnb'!AM{r},\"\")", '0.00'),
        12: (f"=IF(ISNUMBER(K{r}),MAX(K{r},Premissas!$C$13),Premissas!$C$12)", '0.00'),
        13: (f"=IF(Premissas!$C$11=2,L{r},IF(ISNUMBER(K{r}),K{r},Premissas!$C$12))", '0.00'),
        14: (f"=IF(ISNUMBER('Reviews Booking'!AM{r}),'Reviews Booking'!AM{r},\"\")", '0.00'),
        15: (f"=IF(ISNUMBER(N{r}),MAX(N{r},Premissas!$C$16),Premissas!$C$15)", '0.00'),
        16: (f"=IF(Premissas!$C$11=2,O{r},IF(ISNUMBER(N{r}),N{r},Premissas!$C$15))", '0.00'),
        17: (f"=IFERROR(AVERAGE('Buildup Ocupação'!AC{r}:AM{r}),\"\")", '0.0%'),
        18: (f"=IF(ISNUMBER(Q{r}),IF(Q{r}>=Premissas!$C$47,Premissas!$C$48,Premissas!$C$49),Premissas!$C$49)", '0.00'),
        23: (f"=IF(ISNUMBER('Booking Nota Exibida'!AM{r}),'Booking Nota Exibida'!AM{r},\"\")", '0.00'),
        24: (f"=IF(ISNUMBER(W{r}),IF(W{r}>=Premissas!$C$54,1,0),\"\")", '0'),
        10: (f"=IFERROR(SUMPRODUCT('ADR Acomodação'!AH{r}:AK{r},'Ocupação (Disponível)'!AH{r}:AK{r})/SUMPRODUCT('RevPar Mercado'!AH{r}:AK{r},1+'Prêmio de Mercado'!AH{r}:AK{r}),1)", '0.000'),
    }
    for c, (fx, fmt) in f.items():
        x = PP.cell(r, c, fx); x.font = F_CALC; x.number_format = fmt; x.fill = FILL_IN
    for cc in (19, 20):
        x = PP.cell(r, cc, 0); x.font = F_IN; x.fill = FILL_KEY; x.number_format = '0.0%'
    cd_ = ROWINFO[r]['code']; ks_ = [k for k in range(22, 34) if H.get(cd_, {}).get(k) and H[cd_][k]['tot'] > 0]
    if ks_:
        tot_ = sum(H[cd_][k]['tot'] for k in ks_); ex_ = sum(H[cd_][k].get('exp', 0) for k in ks_)
        ot_ = sum(H[cd_][k]['tot'] - H[cd_][k]['air'] - H[cd_][k]['bk'] for k in ks_)
        PP.cell(r, 21, round(ex_ / tot_, 4)).number_format = '0.0%'; PP.cell(r, 22, round((ot_ - ex_) / tot_, 4)).number_format = '0.0%'

# AVERAGE ignora células vazias: volume de reviews deve contar meses sem review como zero
for canal in ('Airbnb', 'Booking'):
    q = AUX[canal][0]
    for r in ROWS:
        cd = ROWINFO[r]['code']
        for k in range(22, K_OUT + 1):
            if q.cell(r, 6 + k).value is None and active(r) and (H.get(cd, {}).get(k)):
                q.cell(r, 6 + k, 0).font = F_IN; AUX[canal][1].cell(r, 6 + k, 0).font = F_IN

# ------------------------------------------------------------------ fórmulas de projeção nas abas de dados
def gcell(r, k):
    y = (K0 + k) // 12
    return f"Premissas!${'C' if y == 2026 else ('D' if y == 2027 else 'E')}${MKT_G[ROWINFO[r]['city']][0]}"
for r in ROWS:
    if not active(r): continue
    for k in range(K_NOV, K_END + 1):
        cl = col(k); m = (K0 + k) % 12
        # mercado
        base = f"'Aux Base Mercado'!{L(6 + (k - K_NOV))}{r}" if k - K_NOV < 12 else f"{col(k - 12)}{r}"
        wb['RevPar Mercado'].cell(r, 6 + k, f"=IFERROR({base}*(1+{gcell(r, k)}),\"\")").font = F_CALC
        # canais
        ds = f"'Premissas por prédio'!$S{r}+'Premissas por prédio'!$T{r}" if k >= 36 else "0"
        wb['% outros'].cell(r, 6 + k, f"=IFERROR(AVERAGE($AC{r}:$AM{r})+{ds},\"\")").font = F_CALC
        for nm in ('% Airbnb', '% Booking'):
            wb[nm].cell(r, 6 + k, f"=IFERROR(AVERAGE($AC{r}:$AM{r})*(1-'% outros'!{cl}{r})/(1-AVERAGE('% outros'!$AC{r}:$AM{r})),\"\")").font = F_CALC
        # reviews 6m
        for canal in ('Airbnb', 'Booking'):
            wb[f'Reviews {canal}'].cell(r, 6 + k, f"=IFERROR(SUM('Aux Soma Notas {canal}'!{col(k-11)}{r}:{cl}{r})/SUM('Aux Qtd Reviews {canal}'!{col(k-11)}{r}:{cl}{r}),\"\")").font = F_CALC
        # prêmio
        idx = f"'Sazonalidade Prêmio Prédio'!${L(6 + m)}{r}"
        basep = f"(1+'Premissas por prédio'!$G{r})*IF(Premissas!$C$23=2,{idx},1)"
        ta = f"IFERROR(Premissas!$C$21*'% Airbnb'!{cl}{r}*('Reviews Airbnb'!{cl}{r}-'Premissas por prédio'!$H{r}),0)"
        tb = f"IFERROR(Premissas!$C$22*'% Booking'!{cl}{r}*('Reviews Booking'!{cl}{r}-'Premissas por prédio'!$I{r}),0)"
        mixf = f"*(1+Premissas!$C$50*'Premissas por prédio'!$S{r}+'Premissas por prédio'!$R{r}*'Premissas por prédio'!$T{r})" if k >= 36 else ""
        bkf = (f"*IFERROR(POWER(1+IF('% Booking'!{cl}{r}>=Premissas!$C$56,Premissas!$C$55,Premissas!$C$57),"
               f"IF('Booking Nota Exibida'!{cl}{r}>=Premissas!$C$54,1,0)-'Premissas por prédio'!$X{r}),1)")
        wb['Prêmio de Mercado'].cell(r, 6 + k, f"=IFERROR({basep}*EXP({ta}+{tb}){mixf}{bkf}-1,\"\")").font = F_CALC

# ------------------------------------------------------------------ Buildup RevPAR
BU = mirror('Buildup RevPAR', 'RevPAR nosso (R$ por noite disponível)',
            'Até ago/26: ADR Acomodação × Ocupação (Report DB). Set/26 em diante: RevPAR Mercado × (1 + Prêmio) × fator de calibração do prédio.')
month_header(BU)
for r in ROWS:
    BU.cell(r, 5, 'R$ por noite disponível')
    for k in range(0, K_END + 1):
        cl = col(k)
        if k <= K_LAST_REAL:
            fx = f"=IF(AND(ISNUMBER('ADR Acomodação'!{cl}{r}),ISNUMBER('Ocupação (Disponível)'!{cl}{r})),'ADR Acomodação'!{cl}{r}*'Ocupação (Disponível)'!{cl}{r},\"\")"
            BU.cell(r, 6 + k, fx).font = F_LINK
        elif active(r):
            fx = f"=IFERROR('RevPar Mercado'!{cl}{r}*(1+'Prêmio de Mercado'!{cl}{r})*'Premissas por prédio'!$J{r},\"\")"
            BU.cell(r, 6 + k, fx).font = F_CALC; BU.cell(r, 6 + k).fill = FILL_IN
        BU.cell(r, 6 + k).number_format = '#,##0.00'
    if not active(r):
        for j in range(1, 6): BU.cell(r, j).fill = PatternFill('solid', fgColor='E7E6E6')

# ------------------------------------------------------------------ Ocupação e ADR
MO = {}
for rr_ in rd('data/ocupacao_predio_mes.psv'):
    MO[(code(rr_['b']), kof(rr_['m']))] = float(rr_['occ'])
def num_(v): return isinstance(v, (int, float))
def occ_real(r, k):
    if k <= K_LAST_REAL:
        v = OCC.cell(r, 6 + k).value
        return v if num_(v) and v > 0 else None
    v = MO.get((ROWINFO[r]['code'], k)); return v if v else None
def fk_of(cd): return kof(FIRST[cd][:7]) if cd in FIRST else None
occ_idx = {}
for city in ('SP', 'FLN', 'BC'):
    rs = [r for r in ROWS if ROWINFO[r]['city'] == city and active(r)]
    ss_r = [r for r in rs if FIRST.get(ROWINFO[r]['code'], '9') < '2025-01-01'] or rs
    prof = {}
    for k in BASE_K:
        v = [occ_real(r, k) for r in ss_r if occ_real(r, k)]
        prof[k] = sum(v) / len(v) if v else None
    base = sum(prof[k] for k in range(30, 34) if prof[k]) / len([k for k in range(30, 34) if prof[k]])
    occ_idx[city] = {k: (prof[k] / base if prof[k] else 1.0) for k in BASE_K}
bo = mirror('Aux Base Ocupação', 'Base de ocupação (nov/25–out/26) para projetar nov/26–out/27',
            'Ocupação realizada da linha (Report DB até ago/26; Metabase em set–out/26). Mês em ramp-up (menos de 3 meses de operação) ou sem dado: média do prédio em jul–out/26 × sazonalidade de ocupação da cidade (verde).')
for i, k in enumerate(BASE_K):
    y = (K0 + k) // 12; m = (K0 + k) % 12
    c = bo.cell(4, 6 + i, f'{MESES[m]}/{str(y)[2:]}'); c.font = F_B; c.fill = FILL_HEAD
bo.cell(4, 18, 'Meses completados').font = F_B
for r in ROWS:
    if not active(r): continue
    cd = ROWINFO[r]['code']; fk = fk_of(cd)
    rec = [occ_real(r, k) for k in range(30, 34) if occ_real(r, k)]
    recent = sum(rec) / len(rec) if rec else None
    nfill = 0
    for i, k in enumerate(BASE_K):
        v = occ_real(r, k)
        ok = v is not None and (fk is None or k - fk >= 3)
        if not ok:
            if recent is None: continue
            v = recent * occ_idx[ROWINFO[r]['city']][k]; nfill += 1
        c = bo.cell(r, 6 + i, round(min(v, 0.97), 4)); c.font = F_IN; c.number_format = '0.0%'
        if not ok: c.fill = FILL_ACT
    bo.cell(r, 18, nfill)

def ogcell(r, k):
    y = (K0 + k) // 12
    return f"Premissas!${'C' if y == 2026 else ('D' if y == 2027 else 'E')}${OCC_G[ROWINFO[r]['city']][0]}"
BO = mirror('Buildup Ocupação', 'Ocupação (noites ocupadas ÷ disponíveis)',
            'Até ago/26: aba Ocupação (Disponível) (Report DB). Set–out/26: realizado no Metabase. Depois: mesmo mês do ano anterior × (1 + variação da cidade em Premissas, item 5), com teto.')
BA = mirror('Buildup ADR', 'ADR Acomodação (R$ por noite ocupada)',
            'Até ago/26: aba ADR Acomodação (Report DB). Set/26 em diante: RevPAR nosso (Buildup RevPAR) ÷ Ocupação (Buildup Ocupação).')
for ws in (BO, BA): month_header(ws)
for r in ROWS:
    BO.cell(r, 5, 'noites ocupadas ÷ disponíveis'); BA.cell(r, 5, 'R$ por noite ocupada')
    for k in range(0, K_END + 1):
        cl = col(k)
        if k <= K_LAST_REAL:
            BO.cell(r, 6 + k, f"=IF(ISNUMBER('Ocupação (Disponível)'!{cl}{r}),'Ocupação (Disponível)'!{cl}{r},\"\")").font = F_LINK
            BA.cell(r, 6 + k, f"=IF(ISNUMBER('ADR Acomodação'!{cl}{r}),'ADR Acomodação'!{cl}{r},\"\")").font = F_LINK
        elif active(r):
            if k <= K_OUT:
                v = MO.get((ROWINFO[r]['code'], k))
                if v:
                    c = BO.cell(r, 6 + k, round(v, 4)); c.font = copy.copy(F_IN); c.fill = FILL_ACT
            else:
                base = f"'Aux Base Ocupação'!{L(6 + (k - K_NOV))}{r}" if k - K_NOV < 12 else f"{col(k - 12)}{r}"
                c = BO.cell(r, 6 + k, f"=IFERROR(MIN(Premissas!$C$33,{base}*(1+{ogcell(r, k)})),\"\")"); c.font = F_CALC; c.fill = FILL_IN
            c = BA.cell(r, 6 + k, f"=IFERROR('Buildup RevPAR'!{cl}{r}/'Buildup Ocupação'!{cl}{r},\"\")"); c.font = F_CALC; c.fill = FILL_IN
            # liga nas abas de input do BP
            for sh, src in (('ADR Acomodação', 'Buildup ADR'), ('Ocupação (Disponível)', 'Buildup Ocupação')):
                x = wb[sh].cell(r, 6 + k)
                x.value = f"=IF(ISNUMBER('{src}'!{cl}{r}),'{src}'!{cl}{r},\"\")"
                f2 = copy.copy(x.font); f2.color = '008000'; x.font = f2
        BO.cell(r, 6 + k).number_format = '0.0%'; BA.cell(r, 6 + k).number_format = '#,##0.00'
    if not active(r):
        for ws in (BO, BA):
            for j in range(1, 6): ws.cell(r, j).fill = PatternFill('solid', fgColor='E7E6E6')
for sh in ('ADR Acomodação', 'Ocupação (Disponível)'):
    wb[sh]['AL3'] = 'Set/26 em diante: puxa do Buildup (Premissas)'

# fonte Arial nas abas novas
for ws in wb.worksheets:
    if ws.title in DATA_SHEETS or ws.title.startswith('Aux') or ws.title in ('Booking Nota Exibida', 'Premissas', 'Premissas por prédio', 'Buildup RevPAR', 'Sazonalidade Prêmio', 'Sazonalidade Prêmio Prédio', 'Buildup Ocupação', 'Buildup ADR'):
        for row in ws.iter_rows():
            for c in row:
                if c.value is not None and (c.font is None or c.font.name != ARIAL):
                    f = copy.copy(c.font); f.name = ARIAL; c.font = f
order = ['Leia-me', 'Premissas', 'Premissas por prédio', 'Sazonalidade Prêmio', 'Sazonalidade Prêmio Prédio', 'Buildup RevPAR', 'Buildup Ocupação', 'Buildup ADR'] + DATA_SHEETS + ['Booking Nota Exibida']
rest = [w for w in wb.sheetnames if w not in order and not w.startswith('Aux')]
aux = [w for w in wb.sheetnames if w.startswith('Aux')]
wb._sheets = [wb[n] for n in order + rest + aux]
for n in aux: wb[n].sheet_properties.tabColor = 'BFBFBF'
for n in ('Premissas', 'Premissas por prédio', 'Sazonalidade Prêmio', 'Sazonalidade Prêmio Prédio', 'Buildup RevPAR', 'Buildup Ocupação', 'Buildup ADR'): wb[n].sheet_properties.tabColor = 'F4CB4F'
wb.active = 1
wb.save(OUT)
print('ok', OUT)
