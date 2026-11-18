# Reviews × prêmio de mercado

Análise feita em 18/nov/2026: como a nota dos hóspedes (Airbnb e Booking) se relaciona com o prêmio de RevPAR
vs mercado, por canal e conforme o peso de cada canal na receita. Publicada como a aba "Reviews × prêmio" do
relatório `../2026-11_premio_mercado/relatorio_premio_mercado.html`.

- `data/reviews_master_month.psv`: reviews Airbnb por anúncio (grupo master) e mês, com subnotas (q1).
- `data/reviews_booking_master_month.psv`: reviews Booking (escala 0–10) por anúncio e mês (q2).
- `data/premio_master_month.psv`: prêmio por anúncio e mês, nov/24–out/26 (q3).
- `data/canal_master_month.psv`: receita de hospedagem por canal (Airbnb, Booking, total) por anúncio e mês (q4).
- `data/caracteristicas_master.psv`: quartos, banheiros, hóspedes e m² de cada anúncio (q5).
- `analysis_tempo.py` gera `tempo.json`: **análise principal, nível prédio** (cada prédio contra ele mesmo ao longo do tempo; janelas de review, Airbnb e Booking, peso do canal, defasagens, ocupação × diária).
- `analysis_robustez.py` gera `robustez.json`: nível anúncio (Airbnb), mesmo anúncio ao longo do tempo, controles de características e janelas.
- `analysis_formula.py` gera `formula.json`: fórmula do efeito no prêmio a partir de %GMV Airbnb/Booking e variação de cada nota (nível prédio, nota 12m), com sorteios do bootstrap para a calculadora; `build_formula.py` monta a seção.
- `analysis_reviews.py` gera `reviews.json` (estimativas com bootstrap por prédio, evolução por prédio, cenários);
  `build_reviews.py` gera `reviews_body.html`, que `../2026-11_premio_mercado/build_relatorio.py` insere na aba.
- `queries.sql`: as queries (Metabase, database 7 = BigQuery; réplicas das tabelas do dashboard 70).

Para atualizar: rode as queries, salve os `.psv` em `data/`, depois
`python3 analysis_reviews.py && python3 analysis_robustez.py && python3 analysis_tempo.py && python3 analysis_formula.py && python3 build_reviews.py && (cd ../2026-11_premio_mercado && python3 build_relatorio.py)`.
