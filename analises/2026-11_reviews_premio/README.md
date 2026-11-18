# Reviews × prêmio de mercado

Análise feita em 18/nov/2026: como a nota dos hóspedes (Airbnb e Booking) se relaciona com o prêmio de RevPAR
vs mercado, por canal e conforme o peso de cada canal na receita. Publicada como a aba "Reviews × prêmio" do
relatório `../2026-11_premio_mercado/relatorio_premio_mercado.html`.

- `data/reviews_master_month.psv`: reviews Airbnb por anúncio (grupo master) e mês, com subnotas (q1).
- `data/reviews_booking_master_month.psv`: reviews Booking (escala 0–10) por anúncio e mês (q2).
- `data/premio_master_month.psv`: prêmio por anúncio e mês, nov/24–out/26 (q3).
- `data/canal_master_month.psv`: receita de hospedagem por canal (Airbnb, Booking, total) por anúncio e mês (q4).
- `analysis_reviews.py` gera `reviews.json` (estimativas com bootstrap por prédio, evolução por prédio, cenários);
  `build_reviews.py` gera `reviews_body.html`, que `../2026-11_premio_mercado/build_relatorio.py` insere na aba.
- `queries.sql`: as queries (Metabase, database 7 = BigQuery; réplicas das tabelas do dashboard 70).

Para atualizar: rode as queries, salve os `.psv` em `data/`, depois
`python3 analysis_reviews.py && python3 build_reviews.py && (cd ../2026-11_premio_mercado && python3 build_relatorio.py)`.
