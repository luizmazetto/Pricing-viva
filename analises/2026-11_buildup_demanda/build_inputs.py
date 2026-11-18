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
for r in rd('data/historico_predio_mes.psv'):
    k = kof(r['m']); c = code(r['b'])
    n, nm = float(r['n']), float(r['n_mkt'])
    d = dict(n=n, rev=float(r['rev']), tot=float(r['rev_tot']), air=float(r['rev_air']), bk=float(r['rev_bk']))
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
    'Reviews Booking': ('Reviews Booking', 'nota 0–10, média móvel 6 meses', '0.00'),
    'Reviews Airbnb': ('Reviews Airbnb', 'nota 1–5, média móvel 6 meses', '0.00'),
    '% Airbnb': ('% Airbnb', '% da receita de hospedagem', '0.0%'),
    '% Booking': ('% Booking', '% da receita de hospedagem', '0.0%'),
    '% outros': ('% outros', '% da receita de hospedagem', '0.0%'),
}
NOTES = {
    'RevPar Mercado': 'RevPAR de mercado = diária mediana fechada × ocupação do mercado (Pricelabs), média das noites disponíveis das nossas unidades. Mesma base do dashboard 58. Projeção: mesmo mês do ano anterior × (1 + variação da cidade em Premissas).',
    'Prêmio de Mercado': 'Prêmio = RevPAR de hospedagem nosso ÷ RevPAR de mercado − 1 (dashboard 58). Projeção: (1 + prêmio base) × exp(β Airbnb × %Airbnb × Δnota Airbnb 12m + β Booking × %Booking × Δnota Booking 12m) − 1.',
    'Reviews Booking': 'Média dos reviews do Booking (general × 2, escala 0–10) criados nos últimos 6 meses. Projeção: nota mensal e volume em Premissas.',
    'Reviews Airbnb': 'Média dos reviews do Airbnb (general, 1–5) criados nos últimos 6 meses. Projeção: nota mensal e volume em Premissas.',
    '% Airbnb': 'Receita de hospedagem de reservas Airbnb ÷ receita de hospedagem total. Projeção: média nov/25–out/26.',
    '% Booking': 'Receita de hospedagem de reservas Booking ÷ receita de hospedagem total. Projeção: média nov/25–out/26.',
    '% outros': 'Demais canais (direto, B2B, corretores, outras OTAs). Projeção: média nov/25–out/26.',
}

def value_for(sheet, c, k):
    h = H.get(c, {}).get(k)
    if sheet == 'RevPar Mercado': return h['mrev'] if h else None
    if sheet == 'Prêmio de Mercado': return (h['rev'] / h['mrev'] - 1) if h and h['mrev'] else None
    if sheet in ('% Airbnb', '% Booking', '% outros'):
        if not h or h['tot'] <= 0: return None
        a, b = h['air'] / h['tot'], h['bk'] / h['tot']
        return {'% Airbnb': a, '% Booking': b, '% outros': max(0.0, 1 - a - b)}[sheet]
    if sheet == 'Reviews Airbnb': return window(RA, c, k, 6)[0]
    if sheet == 'Reviews Booking': return window(RB, c, k, 6)[0]

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
for canal, R, scale_note, nota_cell in (('Airbnb', RA, 'nota 1–5', 'Premissas!$C$11'), ('Booking', RB, 'nota 0–10', 'Premissas!$C$12')):
    q = mirror(f'Aux Qtd Reviews {canal}', f'Quantidade de reviews {canal} por mês',
               'Realizado: reviews criados no mês (Metabase, mesma base do dashboard 70). Projeção: volume mensal de "Premissas por prédio".')
    s = mirror(f'Aux Soma Notas {canal}', f'Soma das notas dos reviews {canal} por mês ({scale_note})',
               'Realizado: soma das notas dos reviews do mês. Projeção: quantidade × nota mensal assumida em Premissas.')
    n12 = mirror(f'Aux Nota 12m {canal}', f'Nota {canal} média móvel 12 meses ({scale_note})',
                 'Janela usada na fórmula do prêmio (foi a janela estimada na análise de reviews × prêmio). Realizado calculado com o histórico desde dez/22.')
    for ws in (q, s, n12): month_header(ws)
    for r in ROWS:
        cd = ROWINFO[r]['code']
        q.cell(r, 5, 'reviews no mês'); s.cell(r, 5, 'soma das notas'); n12.cell(r, 5, scale_note)
        for k in range(0, K_OUT + 1):
            x = R[cd].get(k)
            if x:
                q.cell(r, 6 + k, x[0]).font = F_IN; s.cell(r, 6 + k, round(x[1], 2)).font = F_IN
            v12 = window(R, cd, k, 12)[0]
            if v12 is not None: n12.cell(r, 6 + k, round(v12, 4)).font = F_IN; n12.cell(r, 6 + k).number_format = '0.00'
        if not active(r): continue
        vol_col = 'E' if canal == 'Airbnb' else 'F'
        for k in range(K_NOV, K_END + 1):
            cl = col(k)
            q.cell(r, 6 + k, f"='Premissas por prédio'!${vol_col}{r}").font = F_LINK
            q.cell(r, 6 + k).number_format = '0.0'
            s.cell(r, 6 + k, f"='Aux Qtd Reviews {canal}'!{cl}{r}*{nota_cell}").font = F_CALC
            s.cell(r, 6 + k).number_format = '0.0'
            n12.cell(r, 6 + k, f"=IFERROR(SUM('Aux Soma Notas {canal}'!{col(k-11)}{r}:{cl}{r})/SUM('Aux Qtd Reviews {canal}'!{col(k-11)}{r}:{cl}{r}),\"\")").font = F_CALC
            n12.cell(r, 6 + k).number_format = '0.00'
    AUX[canal] = (q, s, n12)

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
put('B10', '2. Reviews · nota mensal assumida para todos os prédios', F_B)
for c, h in zip('BCDF', ['Canal', 'Nota mensal', 'Escala', 'Racional']):
    put(f'{c}10', h if c != 'B' else '2. Reviews · nota mensal assumida para todos os prédios', F_B, FILL_HEAD if c != 'B' else None)
put('B11', 'Airbnb'); put('C11', 4.75, F_IN, FILL_KEY, '0.00'); put('D11', '1–5')
put('F11', 'Premissa do usuário. Volume mensal por prédio = média de reviews/mês de nov/25–out/26 (aba Premissas por prédio, editável).')
put('B12', 'Booking'); put('C12', 8.5, F_IN, FILL_KEY, '0.0'); put('D12', '0–10')
put('F12', 'Premissa do usuário. Mesmo critério de volume.')
put('B14', '3. Prêmio de mercado', F_B)
put('B15', 'β Airbnb (por estrela × %Airbnb no GMV)'); put('C15', 0.95, F_IN, FILL_KEY, '0.00')
put('F15', 'Estimado na análise Reviews × prêmio (nível prédio, nota 12m): 0,95 (intervalo de 90%: 0,49 a 1,41). Ex.: 50% Airbnb e +0,1★ → +4,9% de prêmio.')
put('B16', 'β Booking (por ponto 0–10 × %Booking no GMV)'); put('C16', 0.0, F_IN, FILL_KEY, '0.00')
put('F16', 'Estimado −0,08 (intervalo −0,19 a +0,02), não significativo: zero por padrão.')
put('B17', 'Base do prêmio: 1 = média jul–out/26 constante · 2 = média jul–out/26 × sazonalidade da cidade'); put('C17', 2, F_IN, FILL_KEY, '0')
put('F17', '1 = sua sugestão, sem sazonalidade. 2 (padrão) = mesma média, ajustada mês a mês pelo padrão do prêmio da cidade (aba Sazonalidade Prêmio). Em FLN o prêmio same store vai de ~0% no verão a ~+40% no inverno: sem isso o RevPAR de jan/fev sai muito alto.')
put('B18', 'Meses da base (opção 1)'); put('C18', 'jul–out/26')
put('B20', '4. Canais', F_B)
put('B21', '% Airbnb, % Booking e % outros'); put('C21', 'média nov/25–out/26, constante')
put('B23', 'Como o prêmio é projetado', F_B)
lines = [
    'Prêmio(t) = (1 + Prêmio base) × exp( β Airbnb × %Airbnb(t) × [Nota Airbnb 12m(t) − Nota Airbnb 12m base] + β Booking × %Booking(t) × [Nota Booking 12m(t) − Nota Booking 12m base] ) − 1',
    'Nota 12m(t) = soma das notas ÷ quantidade de reviews dos últimos 12 meses (abas Aux), com o realizado até out/26 e, depois, volume mensal × nota mensal assumida.',
    'A fórmula usa a nota de 12 meses porque foi a janela em que a relação nota × prêmio apareceu; a de 6 meses (abas Reviews) fica como acompanhamento.',
    'Nota base = média da nota 12m em jul–out/26, o mesmo período do prêmio base: só a mudança de nota a partir de hoje mexe no prêmio.',
    'RevPAR nosso (aba Buildup RevPAR) = RevPAR de mercado × (1 + prêmio) × fator de calibração do prédio, que converte a base do Metabase na base do Report DB (mai–ago/26).',
    'Próximo passo: abrir o RevPAR nosso em Ocupação × ADR (ver sugestão na resposta), antes de levar para as abas de input do BP.',
]
for i, t in enumerate(lines):
    put(f'B{24+i}', t, Font(name=ARIAL, size=10)); P.merge_cells(f'B{24+i}:F{24+i}')
put('B31', 'Legenda', F_B)
put('B32', 'Azul claro = realizado (até ago/26) · Verde claro = realizado em set–out/26 (Metabase) ou base completada · Amarelo = projeção (fórmulas) · Amarelo forte com texto azul = premissa editável', Font(name=ARIAL, size=9))

# ------------------------------------------------------------------ Premissas por prédio
PP = mirror('Premissas por prédio', 'Premissas por prédio', 'Calculadas a partir do realizado; podem ser sobrescritas (ex.: volume de reviews de prédio novo).')
heads = {5: 'Reviews Airbnb/mês (média nov/25–out/26)', 6: 'Reviews Booking/mês (média nov/25–out/26)', 7: 'Prêmio base (média jul–out/26)',
         8: 'Nota Airbnb 12m base (média jul–out/26)', 9: 'Nota Booking 12m base (média jul–out/26)',
         10: 'Fator de calibração RevPAR (Report DB ÷ Mercado × (1+Prêmio), mai–ago/26)'}
for c, h in heads.items():
    x = PP.cell(4, c, h); x.font = F_B; x.fill = FILL_HEAD; x.alignment = Alignment(wrap_text=True, vertical='top'); PP.column_dimensions[L(c)].width = 20
PP.row_dimensions[4].height = 64
for r in ROWS:
    PP.cell(r, 5).value = None
    if not active(r): continue
    f = {
        5: (f"=IFERROR(AVERAGE('Aux Qtd Reviews Airbnb'!AC{r}:AM{r}),0)", '0.0'),
        6: (f"=IFERROR(AVERAGE('Aux Qtd Reviews Booking'!AC{r}:AM{r}),0)", '0.0'),
        7: (f"=IFERROR(AVERAGE('Prêmio de Mercado'!AJ{r}:AM{r}),\"\")", '0.0%'),
        8: (f"=IFERROR(AVERAGE('Aux Nota 12m Airbnb'!AJ{r}:AM{r}),\"\")", '0.00'),
        9: (f"=IFERROR(AVERAGE('Aux Nota 12m Booking'!AJ{r}:AM{r}),\"\")", '0.00'),
        10: (f"=IFERROR(SUMPRODUCT('ADR Acomodação'!AH{r}:AK{r},'Ocupação (Disponível)'!AH{r}:AK{r})/SUMPRODUCT('RevPar Mercado'!AH{r}:AK{r},1+'Prêmio de Mercado'!AH{r}:AK{r}),1)", '0.000'),
    }
    for c, (fx, fmt) in f.items():
        x = PP.cell(r, c, fx); x.font = F_CALC; x.number_format = fmt; x.fill = FILL_IN

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
        for nm in ('% Airbnb', '% Booking', '% outros'):
            wb[nm].cell(r, 6 + k, f"=IFERROR(AVERAGE($AC{r}:$AM{r}),\"\")").font = F_CALC
        # reviews 6m
        for canal in ('Airbnb', 'Booking'):
            wb[f'Reviews {canal}'].cell(r, 6 + k, f"=IFERROR(SUM('Aux Soma Notas {canal}'!{col(k-5)}{r}:{cl}{r})/SUM('Aux Qtd Reviews {canal}'!{col(k-5)}{r}:{cl}{r}),\"\")").font = F_CALC
        # prêmio
        idx = f"'Sazonalidade Prêmio'!${L(2 + m)}${SZROW[ROWINFO[r]['city']]}"
        basep = f"(1+'Premissas por prédio'!$G{r})*IF(Premissas!$C$17=2,{idx},1)"
        ta = f"IFERROR(Premissas!$C$15*'% Airbnb'!{cl}{r}*('Aux Nota 12m Airbnb'!{cl}{r}-'Premissas por prédio'!$H{r}),0)"
        tb = f"IFERROR(Premissas!$C$16*'% Booking'!{cl}{r}*('Aux Nota 12m Booking'!{cl}{r}-'Premissas por prédio'!$I{r}),0)"
        wb['Prêmio de Mercado'].cell(r, 6 + k, f"=IFERROR({basep}*EXP({ta}+{tb})-1,\"\")").font = F_CALC

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

# fonte Arial nas abas novas
for ws in wb.worksheets:
    if ws.title in DATA_SHEETS or ws.title.startswith('Aux') or ws.title in ('Premissas', 'Premissas por prédio', 'Buildup RevPAR', 'Sazonalidade Prêmio'):
        for row in ws.iter_rows():
            for c in row:
                if c.value is not None and (c.font is None or c.font.name != ARIAL):
                    f = copy.copy(c.font); f.name = ARIAL; c.font = f
order = ['Leia-me', 'Premissas', 'Premissas por prédio', 'Sazonalidade Prêmio', 'Buildup RevPAR'] + DATA_SHEETS
rest = [w for w in wb.sheetnames if w not in order and not w.startswith('Aux')]
aux = [w for w in wb.sheetnames if w.startswith('Aux')]
wb._sheets = [wb[n] for n in order + rest + aux]
for n in aux: wb[n].sheet_properties.tabColor = 'BFBFBF'
for n in ('Premissas', 'Premissas por prédio', 'Sazonalidade Prêmio', 'Buildup RevPAR'): wb[n].sheet_properties.tabColor = 'F4CB4F'
wb.active = 1
wb.save(OUT)
print('ok', OUT)
