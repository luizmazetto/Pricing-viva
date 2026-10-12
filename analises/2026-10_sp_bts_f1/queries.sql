-- Queries usadas na extração de 12/out/2026, rodadas pelo Metabase (execute_sql).
-- Para um novo checkpoint, troque: a data de "vendido nos últimos 7 dias" (q1), o T-N de hoje para o BTS (q2, q3)
-- e o T-N da F1 (q4, q5; N = dias entre hoje e 08/11/2026; em 2025 a referência é 09/11/2025).

-- q1 · building_events.psv · Metabase database 7 (BigQuery)
select string_agg(format('%s|%s|%.1f|%.3f|%.3f|%.3f|%s|%s|%.3f|%.0f|%.0f|%.0f|%.0f|%.3f|%s', ev, b, u, occ, occ_mt, l7, coalesce(cast(round(adr) as string),''), coalesce(cast(round(ask) as string),''), mo, mp, p50, p75, p90, coalesce(ab75,0), cast(nights as string)), '\n' order by ev, b) from (
select case when s.date in ('2026-10-30','2026-10-31') then 'BTS' else 'F1' end ev, s.buildingName b,
count(*)/count(distinct s.date) u, avg(occupancy) occ, avg(if(occupancy>0 and reservation.los>=28,1,0)) occ_mt,
avg(if(occupancy>0 and reservation.creation_date >= '2026-10-05',1,0)) l7,
avg(if(occupancy>0, accommodation_adr, null)) adr, avg(if(occupancy=0, our_calendar_price, null)) ask,
avg(market_occupancy) mo, avg(market_median_booked_price) mp, avg(market_pct_50) p50, avg(market_pct_75) p75, avg(market_pct_90) p90,
safe_divide(countif(occupancy=0 and our_calendar_price>market_pct_75), countif(occupancy=0)) ab75, count(*) nights
from `views.listing_daily_stats` s left join `replicas.vivadb_listing` l on s.idlisting=l.id_
where (l.city='São Paulo' or s.city='São Paulo') and availability=1 and s.date in ('2026-10-30','2026-10-31','2026-11-05','2026-11-06','2026-11-07')
group by 1,2);

-- q2 · bts_relative_base.psv (nossa parte, sem mid-term) · database 7
select string_agg(format('%s|%s|%s|%.4f|%.4f|%.4f', per, coalesce(b,'TOTAL'), cast(n as string), o28, o18, ofin), '\n' order by per, b) from (
select if(s.date >= '2026-10-01','BTS','BASE') per, s.buildingName b, countif(not (occupancy>0 and reservation.los>=28)) n,
safe_divide(countif(occupancy>0 and reservation.los<28 and reservation.creation_date <= date_sub(s.date, interval 28 day)), countif(not (occupancy>0 and reservation.los>=28))) o28,
safe_divide(countif(occupancy>0 and reservation.los<28 and reservation.creation_date <= date_sub(s.date, interval 18 day)), countif(not (occupancy>0 and reservation.los>=28))) o18,
safe_divide(countif(occupancy>0 and reservation.los<28), countif(not (occupancy>0 and reservation.los>=28))) ofin
from `views.listing_daily_stats` s left join `replicas.vivadb_listing` l on s.idlisting=l.id_
where (l.city='São Paulo' or s.city='São Paulo') and availability=1 and ((s.date between '2026-07-01' and '2026-09-27' and extract(dayofweek from s.date) in (6,7)) or s.date in ('2026-10-30','2026-10-31'))
group by rollup(1,2) having per is not null);

-- q3 · bts_relative_base.psv (mercado) · database 6 (Postgres, tabela Calendar)
-- base_mkt (T-18) = m21 + (m14 - m21) * 3/7 ; bts_mkt = mo (mkt_occ atual das noites do BTS)
select string_agg(concat_ws('|', per, coalesce(b,'TOTAL'), n_rows, m28, m21, m14, mo), chr(10) order by per, b) from (
select case when "date"::date in ('2026-10-30','2026-10-31') then 'BTS' else 'BASE' end per, "buildingName" b, count(*) n_rows,
round(avg(mkt_occ_pre_28)::numeric,1) m28, round(avg(mkt_occ_pre_21)::numeric,1) m21, round(avg(mkt_occ_pre_14)::numeric,1) m14, round(avg(mkt_occ)::numeric,1) mo
from "Calendar" where city ilike '%paulo%' and coalesce(deleted,false)=false and mkt_occ is not null
and (("date"::date between '2026-07-01' and '2026-09-27' and extract(dow from "date"::date) in (5,6) and mkt_occ_pre_14 is not null) or "date"::date in ('2026-10-30','2026-10-31'))
group by rollup(1,2) having (case when "date"::date in ('2026-10-30','2026-10-31') then 'BTS' else 'BASE' end) is not null) t;

-- q4 · f1_ly_same_store.psv · database 7 (occ_pace = ocupação com reservas criadas até T-27)
select string_agg(format('%d|%s|%.1f|%.3f|%.3f|%.3f|%s|%s|%s|%.3f', y, b, u, occ_fin, occ_pace, occ_mt, coalesce(cast(round(adr_fin) as string),''), coalesce(cast(round(adr_pace) as string),''), coalesce(cast(round(ask) as string),''), mo), '\n' order by b, y) from (
select extract(year from s.date) y, s.buildingName b, count(*)/count(distinct s.date) u,
avg(occupancy) occ_fin,
avg(if(occupancy>0 and reservation.creation_date <= date_sub(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), interval 27 day),1,0)) occ_pace,
avg(if(occupancy>0 and reservation.los>=28,1,0)) occ_mt,
avg(if(occupancy>0, accommodation_adr, null)) adr_fin,
avg(if(occupancy>0 and reservation.creation_date <= date_sub(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), interval 27 day), accommodation_adr, null)) adr_pace,
avg(if(occupancy=0, our_calendar_price, null)) ask,
avg(market_occupancy) mo
from `views.listing_daily_stats` s left join `replicas.vivadb_listing` l on s.idlisting=l.id_
where (l.city='São Paulo' or s.city='São Paulo') and availability=1 and s.date in ('2025-11-06','2025-11-07','2025-11-08','2026-11-05','2026-11-06','2026-11-07')
group by 1,2);

-- q5 · f1_pickup_curve.psv · database 7 (sem mid-term; -1 = não vendido)
select string_agg(format('%d|%d|%d|%.0f', y, lt, n, adr), '\n' order by y, lt) from (
select extract(year from s.date) y,
case when occupancy=0 then -1 when date_diff(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), reservation.creation_date, day) > 60 then 61
when date_diff(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), reservation.creation_date, day) > 33 then 34
when date_diff(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), reservation.creation_date, day) > 27 then 28
when date_diff(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), reservation.creation_date, day) > 21 then 22
when date_diff(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), reservation.creation_date, day) > 14 then 15
when date_diff(if(extract(year from s.date)=2025, date '2025-11-09', date '2026-11-08'), reservation.creation_date, day) > 7 then 8
else 0 end lt,
count(*) n, avg(if(occupancy>0, accommodation_adr, our_calendar_price)) adr
from `views.listing_daily_stats` s left join `replicas.vivadb_listing` l on s.idlisting=l.id_
where (l.city='São Paulo' or s.city='São Paulo') and availability=1 and s.date in ('2025-11-06','2025-11-07','2025-11-08','2026-11-05','2026-11-06','2026-11-07')
and (reservation.los is null or reservation.los<28)
group by 1,2);

-- q6 · market_pace_calendar.psv · database 6
select string_agg(concat_ws('|', d, n, mo, coalesce(m0::text,''), coalesce(m3::text,''), coalesce(m7::text,''), coalesce(m14::text,''), coalesce(m21::text,''), coalesce(m28::text,''), mp), chr(10) order by d) from (select "date"::date d, count(*) n, round(avg(mkt_occ)::numeric,1) mo, round(avg(mkt_occ_pre_0)::numeric,1) m0, round(avg(mkt_occ_pre_3)::numeric,1) m3, round(avg(mkt_occ_pre_7)::numeric,1) m7, round(avg(mkt_occ_pre_14)::numeric,1) m14, round(avg(mkt_occ_pre_21)::numeric,1) m21, round(avg(mkt_occ_pre_28)::numeric,1) m28, round(avg(mkt_price)::numeric,0) mp
from "Calendar" where city ilike '%paulo%' and coalesce(deleted,false)=false and mkt_occ is not null and "date"::date in ('2025-11-06','2025-11-07','2025-11-08','2026-11-05','2026-11-06','2026-11-07','2026-10-30','2026-10-31','2025-10-31','2025-11-01') group by 1) t;
