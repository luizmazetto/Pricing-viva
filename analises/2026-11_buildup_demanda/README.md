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

Cenário (Premissas, C3; valores no item 9): 1 = Base Case (mercado SP −1,1%, FLN −5%, BC +1%; meta de reviews Airbnb 4,75 /
Booking 8,5; Expedia 15% e demais 12% em dez/27). 2 = Bear Case (cada mercado repete 2026 sem crescimento: SP −1,1%,
FLN −10,7%, BC 0%; notas e mix de canais atuais, sem ganho). C11 (reviews) e C65 (canais) seguem C3, mas podem ser sobrescritos.

Coeficientes (19/nov/2026): estimativa conjunta de `analysis_canais_controle_reviews.py` — β Airbnb 1,16; faixa Booking ≥ 8,0
+9,9% (Booking ≥ 35%); Expedia 0,35; demais 0,40 (cheio) / 1,00 (folga, limitado). Antes: 0,95 / 7,5% / 0,41 / 0,41.

Histórico de ADR Acomodação e Ocupação conferido contra a Report DB (VivaProp/Portfolio-Management-Viva, `report_db_short.csv`,
receita de acomodação ÷ diárias e diárias ÷ dias disponíveis por prédio × contrato × mês): jan/24–set/26 bate 100%.
Set/26 vem da Report DB emitida (`data/report_db_predio_mes.psv`); out/26 segue do Metabase até a emissão fechar.
Atenção: em ago/26 a Report DB tem 46 linhas com receita de acomodação e 0 diárias (NXP 950, NXF 444, NUN 61, PQJ 155, KAS 99),
o que infla o ADR desses prédios no mês (NXP R$ 633 vs ~R$ 236).
