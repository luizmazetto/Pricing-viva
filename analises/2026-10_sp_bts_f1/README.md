# SP: BTS (30–31/out/2026) e F1 (5–7/nov/2026)

Análise de pricing por prédio feita em 06/out/2026.

- `data/`: extrações de `views.listing_daily_stats` (BigQuery, base do dashboard 58 "Us vs Market") e da tabela `Calendar` (VivaAnalytics, pace de mercado).
- `classify.py`: aplica as regras de recomendação e gera `recomendacoes.json`.
- `build_html.py` + `template.html`: geram `relatorio_sp_bts_f1.html`.

Para refazer com dados novos: atualize os `.psv` em `data/` e rode `python3 classify.py && python3 build_html.py`.
