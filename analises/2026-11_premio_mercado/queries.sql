-- Queries da extração de 18/nov/2026 (Metabase execute_sql, database 7 = BigQuery).
-- Cada query devolve uma string pipe-separated; o cabeçalho de cada .psv está no README/analysis.py.
-- "YYYY-11p" = nov 1–17 (comparável entre anos); "YYYY-11" = resto de novembro.

-- q1 · data/us_building_month.psv  (header: b|city|m|n|rev|occ|adr|mo|mbp|mrevpar|occ_mt|occ_calc)
select string_agg(format('%s|%s|%s|%d|%.2f|%.4f|%s|%.4f|%.2f|%.2f|%.4f|%.4f', b, city, m, n, rev, occ, coalesce(format('%.2f',adr),''), mo, mbp, mrevpar, occ_mt, occ_calc), '\n' order by b, m) from (
select s.buildingName b, any_value(l.city) city,
 if(date between '2025-11-01' and '2025-11-17' or date between '2026-11-01' and '2026-11-17', format_date('%Y-11p', date), format_date('%Y-%m', date)) m,
 count(*) n, avg(coalesce(accommodation_adr,0)) rev, avg(occupancy) occ, avg(accommodation_adr) adr,
 avg(market_occupancy) mo, avg(market_median_booked_price) mbp, avg(market_median_booked_price*market_occupancy) mrevpar,
 avg(if(occupancy>0 and reservation.los>=28,1,0)) occ_mt, avg(occ_calc) occ_calc
from `views.listing_daily_stats` s join `replicas.vivadb_listing` l on s.idlisting=l.id_
where availability=1 and date between '2024-11-01' and '2026-11-17'
group by 1,3);

-- q2 · data/market_building_cat_month.psv  (header: b|cat|m|n|mbp|p50|occ|rp|tal|nl)
-- mediana entre os nossos listings ativos (vendáveis em out–nov/26) para evitar listings inativos com mercado zerado
with act as (select distinct idlisting listing_id from `views.listing_daily_stats` where availability=1 and date between '2026-10-01' and '2026-11-17'),
pl as (select l.id_ listing_id, l.buildingName b, cast(greatest(p.n_bedrooms,1) as string) cat
  from views.pricelabs_listings_latest p join `replicas.vivadb_listing` l on l.id_=p.listing_id join act on act.listing_id=l.id_ where l.buildingName is not null),
j as (select pl.b, pl.cat, date(o.date) d, o.occupancy/100 occ, f.median_booked_price mbp, f.`50th_percentile` p50, o.total_available_listings tal
  from pl join views.pricelabs_occupancy_latest o on o.listing_id=pl.listing_id and o.category=pl.cat
  join views.pricelabs_future_prices_latest f on f.listing_id=pl.listing_id and f.category=pl.cat and date(f.date)=date(o.date)
  where date(o.date) between '2025-01-01' and '2026-11-17' and f.median_booked_price > 0 and o.occupancy is not null),
bd as (select b, cat, d, count(*) nl,
  approx_quantiles(occ, 2)[offset(1)] occ, approx_quantiles(mbp, 2)[offset(1)] mbp, approx_quantiles(p50, 2)[offset(1)] p50, approx_quantiles(tal, 2)[offset(1)] tal
  from j group by 1,2,3)
select string_agg(format('%s|%s|%s|%d|%.2f|%.2f|%.4f|%.2f|%.1f|%.1f', b, cat, m, n, mbp, p50, occ, rp, tal, nl), '\n' order by b, cat, m) from (
select b, cat, if(d between '2025-11-01' and '2025-11-17' or d between '2026-11-01' and '2026-11-17', format_date('%Y-11p', d), format_date('%Y-%m', d)) m, count(*) n,
  avg(mbp) mbp, avg(p50) p50, avg(occ) occ, avg(occ*mbp) rp, avg(tal) tal, avg(nl) nl
from bd group by 1,2,3);

-- q3 · data/mix_2026.psv  (header: b|cat|n)
select string_agg(format('%s|%s|%d', b, cat, n), '\n' order by b, cat) from (
select s.buildingName b, cast(greatest(n_bedrooms,1) as string) cat, count(*) n
from `views.listing_daily_stats` s where availability=1 and date between '2026-01-01' and '2026-11-17' group by 1,2);

-- q4 · data/first_day.psv  (header: b|first_day)
select s.buildingName b, min(s.date) first_day
from `views.listing_daily_stats` s join `replicas.vivadb_listing` l on s.idlisting=l.id_ where availability=1 group by 1 order by 2;
