# Natal e Réveillon 2026: SP e FLN

Análise de pricing por prédio feita em 06/out/2026. Natal = noites 21–27/dez; Réveillon = 28/dez–3/jan.

- `data/pickup_city.psv`, `data/building_history.psv`: tabela Calendar (pace na mesma data e curvas 2023–2026, sem mid-term).
- `data/market_bq.psv`: `views.listing_daily_stats` (mercado, preço pedido e ADR em 2025 e 2026).
- `classify.py` gera `natal_reveillon.json`; `build_html.py` (com `head.html` + `body.html`) gera `relatorio_natal_reveillon.html`.

Para atualizar nos checkpoints: reextraia os `.psv` com a data do checkpoint no lugar de 06/out e rode `python3 classify.py && python3 build_html.py`.
