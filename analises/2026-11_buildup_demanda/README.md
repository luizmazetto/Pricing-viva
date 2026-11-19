# Buildup de demanda: RevPAR de mercado → reviews → canais → prêmio

Preenche o `Inputs_Demanda.xlsx` (BP PropCo) com o histórico por prédio e projeta nov/26–dez/28 em fórmulas ligadas
à aba `Premissas`. Feito em 18/nov/2026.

- `data/Inputs_Demanda_original.xlsx`: arquivo recebido. `Inputs_Demanda_buildup.xlsx`: saída.
- `data/historico_predio_mes.psv`: por prédio × mês (jan/24–out/26) — RevPAR de hospedagem nosso, RevPAR de mercado e
  receita de hospedagem por canal (`views.listing_daily_stats`, mesma base do dashboard 58).
- Reviews (Airbnb e Booking) e mercado Pricelabs vêm das pastas `../2026-11_reviews_premio/data` e `../2026-11_premio_mercado/data`.
- `build_inputs.py` gera a planilha. Depois rode o recálculo (LibreOffice) para gravar os valores.

Abas preenchidas: RevPar Mercado, Prêmio de Mercado, Reviews Booking/Airbnb (média móvel 12 meses), % Airbnb/Booking/outros.
ADR Acomodação e Ocupação (Disponível): a partir de set/26 puxam de Buildup ADR / Buildup Ocupação.
Realizado até ago/26 só onde a linha (prédio × contrato) tinha ADR no mês; set–out/26 em verde (realizado no Metabase, depois
do fechamento do Report DB). Abas novas: Premissas, Premissas por prédio, Sazonalidade Prêmio, Buildup RevPAR e Aux (cinza).

Reviews: cenário 1 = nota atual (12m) de cada prédio; cenário 2 = meta de portfólio 4,75 (prédios abaixo do piso sobem ao piso, ~4,71).
Prêmio projetado = (1 + média jul–out/26 do prédio) × índice sazonal (do prédio, ou da cidade para prédios novos) × exp(1,16 × %Airbnb × Δnota Airbnb 12m
+ β Booking × %Booking × Δnota Booking 12m) − 1. RevPAR nosso = RevPAR mercado × (1 + prêmio) × fator de calibração
(Report DB ÷ Metabase, mediana mai–ago/26). Ocupação = mesmo mês do ano anterior × (1 + variação da cidade); ADR = RevPAR ÷ Ocupação.
- `data/ocupacao_predio_mes.psv`: ocupação mensal por prédio (Metabase), usada em set–out/26 e na base de prédios em ramp-up.

Canais (Premissas, item 8): cenário 1 = mix de jul–out/26 de cada prédio, constante. Cenário 2 (padrão) = portfólio chega a
15% de Expedia e 12% de demais outros canais em dez/27 (mês editável), em linha reta a partir de nov/26. Cada prédio cresce no
mesmo multiplicador sobre o próprio share de jul–out/26 (hoje 1,37x Expedia e 1,71x demais). Prédios com mais de 50% fora de
Airbnb/Booking (Homelike, Cannes, Equalize) ficam como estão. Airbnb e Booking dividem o resto na proporção atual do prédio.
O ganho no prêmio usa os ganhos líquidos do item 6: × (1 + 0,35 × ΔExpedia + 0,40 ou 1,00 × Δdemais).

Cenário (Premissas, C3; valores no item 9): 1 = Base Case (mercado SP −1,1%, FLN −10,7%, BC +1%; meta de reviews Airbnb 4,75 /
Booking 8,5; Expedia 15% e demais 12% em dez/27). 2 = Bear Case (cada mercado repete 2026 sem crescimento: SP −1,1%,
FLN −10,7%, BC 0%; notas e mix de canais atuais, sem ganho). C11 (reviews) e C65 (canais) seguem C3, mas podem ser sobrescritos.

Coeficientes (19/nov/2026): estimativa conjunta de `analysis_canais_controle_reviews.py` — β Airbnb 1,16; faixa Booking ≥ 8,0
+9,9% (Booking ≥ 35%); Expedia 0,35; demais 0,40 (cheio) / 1,00 (folga, limitado). Antes: 0,95 / 7,5% / 0,41 / 0,41.

Histórico de ADR Acomodação e Ocupação conferido contra a Report DB (VivaProp/Portfolio-Management-Viva, `report_db_short.csv`,
receita de acomodação ÷ diárias e diárias ÷ dias disponíveis por prédio × contrato × mês): jan/24–set/26 bate 100%.
Set/26 vem da Report DB emitida (`data/report_db_predio_mes.psv`); out/26 segue do Metabase até a emissão fechar.
Atenção: em ago/26 a Report DB tem 46 linhas com receita de acomodação e 0 diárias (NXP 950, NXF 444, NUN 61, PQJ 155, KAS 99),
o que infla o ADR desses prédios no mês (NXP R$ 633 vs ~R$ 236). Corrigido só na planilha (Report DB fica como emitida): diárias e dias disponíveis dessas 41 unidades vêm da calendar do
Metabase (bate 100% com a Report DB em jul e set/26); ADR e ocupação de ago/26 recalculados (células em laranja com comentário).

2028 (Base Case, cenário de canais 2): notas ficam no nível de dez/27 (4,75 / 8,5); Expedia fica em 15%; demais outros canais
sobem de 12% (dez/27) para 16% em dez/28, em linha reta (Premissas C77; multiplicador D77 sobre o share de jul–out/26).

Mercado de FLN: −10,7% em nov/26–dez/27 e −5% em 2028, nos dois cenários (Premissas, item 9, linhas 82–87: por cidade, 2027 e 2028).

Teto de 25% no share de demais outros canais por prédio (Premissas C89, Base Case), com redistribuição do excedente entre os prédios que crescem (multiplicadores C73/D77, iterações em H/I).

Comissão de Canais %, LOS, Taxa de Limpeza por reserva e OTA Taxa Limpeza % (Premissas, item 10). Set/26 da Report DB emitida;
projeção de out/26 a dez/28:
- Comissão = (OTAs Fee + Custo Canal Tx Limpeza) ÷ Total. Projeção: base jul–set/26 do prédio × índice de mix (taxa efetiva por
  canal × % do canal no mês) ÷ índice na base. Taxas (Metabase, commissionValue ÷ GMV total, check-in ago–out/26): Airbnb 18,1%, Booking 17,8%
  (subiu de ~13% em 2025 para ~18% em ago–out/26), Expedia 16,4%, demais 12,8%. Base de comissão do prédio: ago–set/26. Segue sozinha o cenário de canais. OTA Taxa Limpeza (Custo Canal Tx Limpeza ÷ Receita de Limpeza,
  só Revenue Model, aba com linhas próprias): mesma regra.
- LOS = diárias ÷ reservas. Base Case: mesmo mês do ano anterior × (1 + 4,9% × (1 − 50%)) = +2,45% a.a.; Bear: igual ao ano anterior.
- Taxa de Limpeza por reserva = receita de limpeza ÷ reservas. Média jul–set/26 do prédio, reajuste de 4,5% em jan/27 e jan/28.
- Ago–set/26: a Report DB tem ~220 unidades/mês com diárias e 0 reservas (16 prédios). Reservas completadas com a calendar do Metabase
  (reservas com noite no mês, mesma definição; bate 93–97% por unidade em mai–jul/26): data/report_db_reservas_ajuste.psv.

Demais outros canais divididos em canal direto (Viva: 0. Direct, Direct - empresas, 1. Extensão, Website, Reserva Interna) e outros
canais (Swap, Quinto Andar, DIVID, Homelike, Decolar, API B2B, Cangooroo...): Premissas, item 11; aba Aux % Direto. Hoje (jul–out/26)
direto 2,7% e outros 5,3% da receita de hospedagem. Metas: dez/27 direto 5% + outros 7% = 12%; dez/28 16% na mesma proporção
(6,7% / 9,3%). Custo (commissionValue ÷ GMV, check-in ago–out/26): direto 11,8%, outros canais 13,2%. Base: data/demais_direto_outros_jul_out26.psv.

Swap ("0.1. Swap") = reserva espelho de realocação (hóspede trocado de unidade), clonada da reserva original. Devolvida ao canal original
em historico_predio_mes.psv (código HM… na nota interna → Airbnb; número de 9–10 dígitos → Booking; não identificada (5%) → 56,5/43,5).
Era 2,3% da receita de hospedagem em jul–out/26. Demais outros canais sem a Swap: 5,7% (direto 2,7%, outros 3,0%). Coeficientes
reestimados sem a Swap: β Airbnb 1,08; Expedia 0,31; demais 0,41 (cheio) / 1,00 (folga); faixa Booking +9,5%.
