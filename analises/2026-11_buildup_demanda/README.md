# Buildup de demanda: RevPAR de mercado → reviews → canais → prêmio

Preenche o `Inputs_Demanda.xlsx` (BP PropCo) com o histórico por prédio e projeta nov/26–dez/28 em fórmulas ligadas
à aba `Premissas`. Feito em 18/nov/2026.

- `data/Inputs_Demanda_original.xlsx`: arquivo recebido. `Inputs_Demanda_buildup.xlsx`: saída.
- `data/historico_predio_mes.psv`: por prédio × mês (jan/24–out/26) — RevPAR de hospedagem nosso, RevPAR de mercado e
  receita de hospedagem por canal (`views.listing_daily_stats`, mesma base do dashboard 58).
- Reviews (Airbnb e Booking) e mercado Pricelabs vêm das pastas `../2026-11_reviews_premio/data` e `../2026-11_premio_mercado/data`.
- `build_inputs.py` gera a planilha. Depois rode o recálculo (LibreOffice) para gravar os valores.

Abas preenchidas: RevPar Mercado, Prêmio de Mercado, Reviews Booking/Airbnb (média móvel 6 meses), % Airbnb/Booking/outros.
Realizado até ago/26 só onde a linha (prédio × contrato) tinha ADR no mês; set–out/26 em verde (realizado no Metabase, depois
do fechamento do Report DB). Abas novas: Premissas, Premissas por prédio, Sazonalidade Prêmio, Buildup RevPAR e Aux (cinza).

Prêmio projetado = (1 + média jul–out/26 do prédio) × índice sazonal da cidade × exp(0,95 × %Airbnb × Δnota Airbnb 12m
+ β Booking × %Booking × Δnota Booking 12m) − 1. RevPAR nosso = RevPAR mercado × (1 + prêmio) × fator de calibração
(Report DB ÷ Metabase, mai–ago/26).
