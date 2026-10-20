# SP: BTS (30–31/out/2026) e F1 (5–7/nov/2026)

Análise de pricing por prédio feita em 06/out/2026 e atualizada em 12/out (BTS a T-18, F1 a T-27) 15/out (BTS a T-15, F1 a T-24) 18/out (BTS a T-12, F1 a T-21) e 20/out/2026 (BTS a T-10, F1 a T-19). A cada rodada, a recomendação anterior fica em `data/recomendacoes_anterior.json` para a comparação "o que mudou".

- `data/`: extrações de `views.listing_daily_stats` (BigQuery, base do dashboard 58 "Us vs Market") e da tabela `Calendar` (VivaAnalytics, pace de mercado).
- `classify.py`: aplica as regras de recomendação e gera `recomendacoes.json`.
- `build_html.py` + `template.html`: geram `relatorio_sp_bts_f1.html`.
- `queries.sql`: as queries da extração (Metabase, databases 6 e 7).

Para refazer com dados novos: rode as queries de `queries.sql` com a data do checkpoint, atualize os `.psv` em `data/` (e os textos de `template.html`/`classify.py` que citam T-18/T-27) e rode `python3 classify.py && python3 build_html.py`.
