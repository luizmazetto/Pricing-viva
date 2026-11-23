# Teste: redução do markup do Airbnb (22% → 10%), SP e FLN

Desenhado em 23/nov/2026. Contexto: depois de 13/out/2026 (última onda da migração do Airbnb para a taxa única do anfitrião),
as vendas da Viva no Airbnb caíram ~41% vs 2025 (SP e FLN), enquanto Booking/Expedia cresceram. A conta da Viva sempre esteve na
taxa única; os concorrentes passaram a embutir a taxa do hóspede na diária, e a PriceLabs passou a medir o mercado já com a taxa
(+16% no preço de mercado de SP vs 2025). Nossos preços acompanharam esse salto e ficaram ~10–13% mais caros para o hóspede vs a
posição usual nesta época. Hipótese testada: devolver ~10% no preço do Airbnb (markup 22% → 10%) recupera volume suficiente
(empate: +11% de noites no Airbnb).

- `grupos.csv`: prédios por grupo. Teste (16 SP + 6 FLN, ~70% das unidades, inclui todos os mais afetados) e controle (6 SP + 2 FLN),
  pareados por % Airbnb, diária e queda no Airbnb antes do teste. "fora" = mantidos em 22% e acompanhados.
- `acompanhamento.sql`: consulta semanal (Metabase, database 7). Edite `inicio` (dia da mudança) e `fln_ate`.
  Resumo: índice depois/base (base = 4 semanas antes) e efeito vs controle para Airbnb, Booking e receita total.

## Leitura
- Principal: `teste` vs `controle` (quedas iguais antes do teste: 0,65 × 0,65). `teste_mais_afetado` é secundário (tende a
  recuperar sozinho; o efeito ali fica superestimado).
- Ruído: rodando a consulta com início fictício em 02/nov (sem mudança nenhuma), o "efeito" em SP saiu entre −10% e −5%;
  em FLN entre −37% e −27% (poucos prédios). Em SP, só considerar efeito real acima de ~+15–20% depois de 3 semanas;
  em FLN o teste só detecta efeitos muito grandes, então ler junto com SP.
- Decisão em 3 semanas: Airbnb > +11% vs controle → manter e estender; > +25% sem perda no Booking → testar 7%;
  sem reação → problema de ranking (checar Insights do Airbnb) e voltar a 22%.
- FLN: se o markup puder ser limitado por data, aplicar só até 19/dez (temporada à frente de 2025); a consulta filtra
  as estadias de FLN até `fln_ate`.
