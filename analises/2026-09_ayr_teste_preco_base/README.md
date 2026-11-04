# AYR 423 (Ayra Pinheiros): teste de preço base, 09/set a 05/out/2026

Em 08/set (22h) o preço base dos anúncios do AYR no PriceLabs subiu ~10% (R$ 516 para R$ 568, média ponderada por unidade) para medir a sensibilidade a preço. Em 06/out (13h) ele voltou a R$ 520. Esta pasta tem a análise do resultado para o proprietário, em 1 slide no Viva Design System dos pitches do Growth.

## Desenho

- **Fonte dos resultados:** tabela `Calendar` (VivaAnalytics, Metabase database 6). Diária = `dailyRate`. Inventário = `status in ('available','booked')`, sem `deleted`. Estadias de 28 noites ou mais (mid-term) ficam de fora.
- **Mesmas unidades:** 28 unidades do AYR e cerca de 830 do Viva SP com operação nas janelas antes e depois (sem as 9 unidades que entraram entre ago e out).
- **Janelas de estadia:** antes de 10/ago a 08/set, teste de 09/set a 05/out e depois de 06/out a 02/nov.
- **Noites atípicas excluídas:** feriado de 7/set (04 a 07/set), 1º turno das eleições (02 a 05/out), feriado de 12/out (10 a 12/out), BTS e Finados (30/out a 02/nov). O efeito eleitoral está no fim de semana de 04/out: o mercado caiu para 43 a 49% de ocupação.
- **Comparações:** compset do PriceLabs (`mkt_occ`, `mkt_price` da Calendar) e o restante do portfólio Viva em SP como controle (diferença em diferenças).
- **Data da reserva:** noites vendidas por janela de criação da reserva (12/ago a 08/set, 09/set a 06/out e 07/out a 03/nov).
- **Preço base:** log do PriceLabs (`get_user_logs`, ação `base_price`).

## Resultado (estadia, sem as noites atípicas)

| | Antes | Teste | Depois |
|---|---|---|---|
| Ocupação AYR | 81,6% | 71,4% | 80,1% |
| Ocupação mercado | 67,2% | 65,5% | 64,3% |
| ADR AYR | R$ 417 | R$ 400 | R$ 390 |
| Prêmio de diária vs mercado | 1,35x | 1,34x | 1,17x |
| RevPAR AYR | R$ 340 | R$ 285 | R$ 312 |
| RevPAR vs mercado | 1,63x | 1,45x | 1,43x |
| Ocupação Viva SP | 81,5% | 80,5% | 81,1% |
| Noites vendidas (data da reserva) | 515 | 354 (−31%) | 449 |

No mesmo período, as noites vendidas no Viva SP caíram 4%. A receita perdida foi estimada entre R$ 17,8 mil (contrafactual: variação do Viva SP) e R$ 20,7 mil (contrafactual: manter o índice de RevPAR vs mercado), nas 595 noites comparáveis do teste.

No período depois, o prêmio de diária caiu para 1,17x porque o mercado subiu no fim de outubro (eventos) e o AYR não acompanhou. Isso dá base para a recomendação de buscar prêmio por data, e não no preço base.

## Arquivos

- `queries.sql`: as queries da extração.
- `data/*.psv`: saídas das queries.
- `build_slide.py`: gera `slide_ayr_teste_preco_base.html`. Depois, `node render.js` gera o PNG e o PDF (com `NODE_PATH=$(npm root -g)` se o Playwright for global).
