# Fim de semana do 2º turno (25/out/2026): prédios com ocupação baixa

Mapeamento feito em 13/out/2026 (T-10 para a sexta 23/out, T-11 para o sábado 24/out) para escolher onde incentivar vendas.
Foco nas noites de sex 23 e sáb 24; a noite de domingo 25 aparece só como contexto em `eleicoes.json` (`occ_25`).

## O que os dados dizem

- **Fim de semana de eleição é fraco, mas o pace de agora não mostra isso.** No 1º turno (2–3/out/2026), SP chegou em T-10 com 24%/18%, igual a um fim de semana normal, e fechou em 72%/64% (os normais de setembro fecharam em ~78%); o mercado fechou em 48%/44% contra ~62–67%. A perda veio na reta final. No 2º turno de 2024 em SP (25–26/out/2024) fechamos em 75% contra 91–96% nos fins de semana vizinhos.
- **Hoje:** SP está com 21%/17% (normal em T-10: ~22%) e FLN com 15%/12% (normal: ~25%). FLN já está atrás do ritmo.
- **Projeção:** ocupação de hoje + pickup normal do prédio × fator eleição (o pickup do 1º turno foi 85% do normal em SP e 81% em FLN).

## Critérios

- **Crítico:** projeção de fechamento < 50% e abaixo do ritmo normal, ou zerado com 10+ noites livres.
- **Atenção:** projeção < 60%, ou 5+ p.p. abaixo do ritmo normal, ou nenhuma venda nos últimos 7 dias estando abaixo do ritmo.
- Ação: preço pedido (PriceLabs) > 15% acima do preço de mercado → baixar; senão, incentivo comercial. Com estadia mínima de 2 noites, liberar 1 noite.
- Ficam de fora: unidades só de mid-term (estadia mínima 90: MEL, MOU, PED), EQL 130 (sem histórico), prédio de teste do Rio e ZOM.

## Resultado

Tabela completa em [`tabela.md`](tabela.md); dados por prédio em `eleicoes.json`.

## Arquivos

- `data/now_23_24.psv`: noites 23–24/out hoje, noite 25/out e fechamento do 1º turno (2–3/out), por prédio.
- `data/base_weekends.psv`: sextas e sábados de 01/ago a 03/out/2026, com pace em T-10/T-11 e fechamento.
- `data/city_weekends.psv`: série por cidade (inclui 2º turno de 2024 em SP).
- `queries.sql`: as queries (Metabase, database 6, tabela `Calendar`).
- `classify.py`: gera `eleicoes.json` e `tabela.md`.

Para atualizar: rode as queries de `queries.sql` (trocando a data de corte das "vendas 7d" e o T-N do pace), atualize os `.psv` e rode `python3 classify.py`.
