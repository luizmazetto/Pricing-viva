-- Extração de 04/nov/2026, rodada no Metabase (execute_sql), database 6 (Postgres, tabela "Calendar").
-- Lista de noites atípicas excluídas (usada em todas as queries):
--   '2026-09-04'..'2026-09-07' (feriado 7/set), '2026-10-02'..'2026-10-05' (eleição 04/out),
--   '2026-10-10'..'2026-10-12' (feriado 12/out), '2026-10-30'..'2026-11-02' (BTS/Finados) [+ '2026-11-05'..'2026-11-08' F1 na q2]

-- q1 · data/periodos_estadia.psv
with c as (
select case when "buildingName"='AYR 423 - Ayra Pinheiros' then 'AYR' else 'SP' end g, idlisting, "date"::date d, status::text st, coalesce(los,0) los, "dailyRate" rate, "creationDate"::date cd, mkt_occ, mkt_price, mkt_occ_pre_7, mkt_occ_pre_14
from "Calendar" where city ilike '%paulo%' and coalesce(deleted,false)=false and status::text in ('available','booked') and "date" between '2026-08-10' and '2026-11-02'),
ss as (select idlisting from c group by 1 having count(*) filter (where d between '2026-08-10' and '2026-09-08') >= 20 and count(*) filter (where d between '2026-10-06' and '2026-11-02') >= 20),
x as (select c.*, case when d <= '2026-09-08' then '1PRE' when d <= '2026-10-05' then '2TESTE' else '3POS' end per from c join ss using(idlisting)
 where d not in ('2026-09-04','2026-09-05','2026-09-06','2026-09-07','2026-10-02','2026-10-03','2026-10-04','2026-10-05','2026-10-10','2026-10-11','2026-10-12','2026-10-30','2026-10-31','2026-11-01','2026-11-02')
 and not (st='booked' and los>=28))
select g, per, count(distinct idlisting) nl, count(*) n,
round(avg(case when st='booked' then 1.0 else 0 end),4) occ,
round(avg(case when st='booked' then rate end)::numeric,1) adr,
round((sum(case when st='booked' then rate else 0 end)/count(*))::numeric,1) revpar,
round(avg(mkt_occ)::numeric,2) mo, round(avg(mkt_price)::numeric,1) mp, round(avg(mkt_occ*mkt_price/100)::numeric,1) mrevpar,
round(avg(case when st='booked' and cd <= d - 7 then 1.0 else 0 end),4) occ7,
round(avg(case when st='booked' and cd <= d - 14 then 1.0 else 0 end),4) occ14,
round(avg(mkt_occ_pre_7)::numeric,2) mo7, round(avg(mkt_occ_pre_14)::numeric,2) mo14
from x group by 1,2 order by 1,2;

-- q2 · data/periodos_venda.psv (noites vendidas por janela de criação da reserva; coluna prem_invalid não é usada)
with c as (
select case when "buildingName"='AYR 423 - Ayra Pinheiros' then 'AYR' else 'SP' end g, idlisting, "date"::date d, status::text st, coalesce(los,0) los, "dailyRate" rate, "creationDate"::date cd, mkt_price
from "Calendar" where city ilike '%paulo%' and coalesce(deleted,false)=false and status::text in ('available','booked') and "date" between '2026-07-27' and '2027-03-31'),
ss as (select idlisting from c group by 1 having count(*) filter (where d between '2026-08-10' and '2026-09-08') >= 20 and count(*) filter (where d between '2026-10-06' and '2026-11-02') >= 20),
x as (select c.*, case when cd between '2026-08-12' and '2026-09-08' then '1PRE' when cd between '2026-09-09' and '2026-10-06' then '2TESTE' when cd between '2026-10-07' and '2026-11-03' then '3POS' end per
 from c join ss using(idlisting) where st='booked' and los<28
 and d not in ('2026-09-04','2026-09-05','2026-09-06','2026-09-07','2026-10-02','2026-10-03','2026-10-04','2026-10-05','2026-10-10','2026-10-11','2026-10-12','2026-10-30','2026-10-31','2026-11-01','2026-11-02','2026-11-05','2026-11-06','2026-11-07','2026-11-08'))
select g, per, count(distinct idlisting) nl, count(*) nights, round(avg(rate)::numeric,1) adr,
round(avg(d - cd)::numeric,1) lead, round(avg(case when d - cd <= 7 then 1.0 else 0 end),3) sh7
from x where per is not null group by 1,2 order by 1,2;

-- q3 · data/semanal.psv (semanas de quarta a terça, alinhadas ao início do teste em 09/set)
with c as (
select case when "buildingName"='AYR 423 - Ayra Pinheiros' then 'AYR' else 'SP' end g, idlisting, "date"::date d, status::text st, coalesce(los,0) los, "dailyRate" rate, mkt_occ, mkt_price
from "Calendar" where city ilike '%paulo%' and coalesce(deleted,false)=false and status::text in ('available','booked') and "date" between '2026-07-15' and '2026-11-03'),
ss as (select idlisting from c group by 1 having count(*) filter (where d between '2026-08-10' and '2026-09-08') >= 20 and count(*) filter (where d between '2026-10-06' and '2026-11-02') >= 20),
x as (select c.*, d - ((extract(dow from d)::int + 4) % 7) wk from c join ss using(idlisting) where not (st='booked' and los>=28)
 and d not in ('2026-09-04','2026-09-05','2026-09-06','2026-09-07','2026-10-02','2026-10-03','2026-10-04','2026-10-05','2026-10-10','2026-10-11','2026-10-12','2026-10-30','2026-10-31','2026-11-01','2026-11-02'))
select g, wk, count(*) n, round(avg(case when st='booked' then 1.0 else 0 end),3) occ, round(avg(case when st='booked' then rate end)::numeric,0) adr,
round(avg(mkt_occ)::numeric,1) mo, round(avg(mkt_price)::numeric,0) mp
from x group by 1,2 order by 1,2;   -- a semana de 28/out (eventos, parcial) fica fora do gráfico

-- Apoio, sem uso no slide: data/preco_publicado_vs_mercado.psv. Preço de 1 noite publicado na Stays (import.stays_calendar_raw)
-- para noites de 7 a 21 dias à frente ÷ market_pct_50 (views.listing_daily_stats), database 7 (BigQuery), por dia do snapshot.
-- Dá 1,44x antes, 1,46x na 1ª semana do teste e 1,39x no resto. Inclui noites já vendidas, então é só indicativo.
