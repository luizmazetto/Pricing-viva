# Prêmio de mercado 2026: same store, prédios novos e mercados

Análise feita em 18/nov/2026, logo depois da atualização dos dados de mercado do Pricelabs (nova metodologia).
Compara 2026 vs 2025 em jan–out (meses fechados) e nov 1–17.

- Prêmio = nosso RevPAR de hospedagem ÷ RevPAR de mercado, mesma conta do card 705 do dashboard 58 "Us vs. Market"
  (`views.listing_daily_stats`, `availability = 1`).
- Same store = 24 prédios com primeira noite antes de 1/jan/2025. Prédios novos = entradas de fev/2025 em diante.
- Mercado = `views.pricelabs_future_prices_latest` + `views.pricelabs_occupancy_latest`, mediana entre os nossos listings
  ativos por prédio × categoria × dia, com mix de categorias fixo de 2026.

Arquivos:
- `data/us_building_month.psv`: nosso lado + mercado por prédio e mês (q1).
- `data/market_building_cat_month.psv`: mercado Pricelabs por prédio, categoria e mês (q2).
- `data/mix_2026.psv`: unidades × noites por prédio e categoria em 2026 (q3). `data/first_day.psv`: primeira noite de cada prédio (q4).
- `analysis.py` gera `analise.json`; `build_html.py` + `template.html` geram `relatorio_premio_mercado.html`.
- `queries.sql`: as queries (Metabase, database 7 = BigQuery).

Para atualizar: rode as queries trocando as datas de corte (hoje 2026-11-17), salve os `.psv` em `data/` e rode
`python3 analysis.py && python3 build_html.py`. Os textos do resumo são montados a partir dos números, mas revise a
redação (ex.: "SP virou em outubro") se a história mudar.
