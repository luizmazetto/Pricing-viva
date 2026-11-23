-- Teste de redução do markup do Airbnb (22% -> 10%) · acompanhamento semanal
-- Metabase database 7 (BigQuery). Edite só o bloco "params": data de início do teste e fim da janela de estadias de FLN.
-- Saída 1 (semanal): noites curtas (<28) vendidas por semana de criação, por unidade, por cidade × grupo × canal.
-- Saída 2 (resumo): base = 4 semanas antes do início; índice depois/base; diferença-em-diferenças teste vs controle.
with params as (
  select date '2026-11-25' as inicio,          -- dia em que o markup mudou nos prédios de teste
         date '2026-12-19' as fln_ate          -- FLN: se o markup reduzido valer só até essa data de estadia
),
grupos as (
  select * from unnest([
    -- SP · teste (mais afetados)
    struct('SP' as c, 'NXD 382' as cod, 'teste_mais_afetado' as g), ('SP','FYP 441','teste_mais_afetado'), ('SP','PQJ 155','teste_mais_afetado'),
    ('SP','NXF 444','teste_mais_afetado'), ('SP','NXB 1333','teste_mais_afetado'), ('SP','HBV 189','teste_mais_afetado'), ('SP','SPZ 648','teste_mais_afetado'),
    -- SP · teste (demais)
    ('SP','AGR 965','teste'), ('SP','AYM 181','teste'), ('SP','HLK 407','teste'), ('SP','NXP 950','teste'), ('SP','OMG 45','teste'),
    ('SP','PVF 1304','teste'), ('SP','PVJ 44','teste'), ('SP','PVP 936','teste'), ('SP','SCN 59','teste'),
    -- SP · controle
    ('SP','KAS 99','controle'), ('SP','NUN 61','controle'), ('SP','NXH 720','controle'), ('SP','ONZ 247','controle'), ('SP','PVN 39','controle'), ('SP','TOF 1485','controle'),
    -- SP · fora do teste (acompanhados)
    ('SP','AYR 423','fora'), ('SP','AYH 634','fora'), ('SP','CNZ 366','fora'), ('SP','DGE 197','fora'), ('SP','URB 172','fora'), ('SP','NXV 601','fora'),
    -- FLN · teste (mais afetados vs 2025)
    ('FLN','CAN 203','teste_mais_afetado'), ('FLN','ARB 301','teste_mais_afetado'), ('FLN','AGM 85','teste_mais_afetado'), ('FLN','ZEE 135','teste_mais_afetado'),
    -- FLN · teste (demais)
    ('FLN','FST 3950','teste'), ('FLN','AQL 1420','teste'),
    -- FLN · controle
    ('FLN','TBG 1320','controle'), ('FLN','TPV 869','controle')
  ])
),
base as (
  select g.c, g.g, s.idlisting, s.date, s.availability, s.occupancy, s.accommodation_adr adr,
         reservation.creation_date cd, reservation.los los,
         case when reservation.source in ('API airbnb','Airbnb') then 'airbnb'
              when reservation.source in ('API booking.com','Booking.com') then 'booking'
              else 'outros' end canal
  from `views.listing_daily_stats` s
  join grupos g on regexp_extract(s.buildingName, r'^(\S+ \d+)') = g.cod
  cross join params p
  where s.date >= date_sub(p.inicio, interval 28 day)
    and (g.c = 'SP' or s.date <= p.fln_ate or reservation.creation_date is null)   -- FLN: só estadias na janela do teste
),
unid as (   -- unidades ativas por grupo (média de unidades disponíveis por noite, próximos 60 dias a partir do início)
  select c, g, count(*) / 60 unidades
  from base, params p where date between p.inicio and date_add(p.inicio, interval 59 day) and availability = 1 group by 1,2
),
vendas as (
  select c, g, canal, date_trunc(cd, week(monday)) semana, count(*) noites, sum(adr) receita
  from base, params p
  where occupancy > 0 and los < 28 and cd >= date_sub(p.inicio, interval 28 day)
    and cd < date_trunc(current_date('America/Sao_Paulo'), week(monday))   -- só semanas completas
  group by 1,2,3,4
),
semanal as (
  select v.c, v.g, v.semana, u.unidades,
    round(sum(if(canal='airbnb', noites, 0)) / u.unidades, 3) airbnb_noites_unid,
    round(sum(if(canal='booking', noites, 0)) / u.unidades, 3) booking_noites_unid,
    round(sum(noites) / u.unidades, 3) total_noites_unid,
    round(sum(if(canal='airbnb', receita, 0)) / u.unidades, 1) airbnb_receita_unid,
    round(sum(receita) / u.unidades, 1) total_receita_unid,
    round(safe_divide(sum(if(canal='airbnb', receita, 0)), sum(if(canal='airbnb', noites, 0))), 0) airbnb_adr
  from vendas v join unid u using (c, g)
  group by 1,2,3,4
),
resumo as (
  select c, g,
    avg(if(semana <  (select date_trunc(inicio, week(monday)) from params), airbnb_noites_unid, null)) abb_base,
    avg(if(semana >= (select date_trunc(inicio, week(monday)) from params), airbnb_noites_unid, null)) abb_depois,
    avg(if(semana <  (select date_trunc(inicio, week(monday)) from params), booking_noites_unid, null)) bkg_base,
    avg(if(semana >= (select date_trunc(inicio, week(monday)) from params), booking_noites_unid, null)) bkg_depois,
    avg(if(semana <  (select date_trunc(inicio, week(monday)) from params), total_receita_unid, null)) rec_base,
    avg(if(semana >= (select date_trunc(inicio, week(monday)) from params), total_receita_unid, null)) rec_depois
  from semanal group by 1,2
)
-- Saída 2 (resumo). Para a Saída 1, troque o select final por: select * from semanal order by c, g, semana
select r.c cidade, r.g grupo,
  round(r.abb_base, 3) airbnb_base, round(r.abb_depois, 3) airbnb_depois, round(safe_divide(r.abb_depois, r.abb_base), 3) airbnb_indice,
  round(safe_divide(safe_divide(r.abb_depois, r.abb_base), safe_divide(k.abb_depois, k.abb_base)) - 1, 3) airbnb_efeito_vs_controle,
  round(safe_divide(r.bkg_depois, r.bkg_base), 3) booking_indice,
  round(safe_divide(safe_divide(r.bkg_depois, r.bkg_base), safe_divide(k.bkg_depois, k.bkg_base)) - 1, 3) booking_efeito_vs_controle,
  round(safe_divide(safe_divide(r.rec_depois, r.rec_base), safe_divide(k.rec_depois, k.rec_base)) - 1, 3) receita_total_efeito_vs_controle
from resumo r left join resumo k on k.c = r.c and k.g = 'controle'
order by 1, 2
