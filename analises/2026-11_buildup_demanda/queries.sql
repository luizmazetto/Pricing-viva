-- historico_predio_mes.psv (header: b|m|n|rev|mrevpar|rev_air|rev_bk|rev_tot|n_mkt) · Metabase database 7 (BigQuery)
select string_agg(format('%s|%s|%d|%.4f|%s|%.0f|%.0f|%.0f|%d', b, m, n, rev, coalesce(format('%.4f', mrevpar),''), rev_air, rev_bk, rev_tot, n_mkt), '\n' order by b, m) from (
select s.buildingName b, format_date('%Y-%m', date) m, count(*) n, avg(coalesce(accommodation_adr,0)) rev,
 avg(if(market_occupancy is not null and market_median_booked_price is not null, market_median_booked_price*market_occupancy, null)) mrevpar,
 countif(market_occupancy is not null) n_mkt,
 sum(if(occupancy>0 and reservation.source like '%airbnb%', accommodation_adr, 0)) rev_air,
 sum(if(occupancy>0 and reservation.source like '%booking%', accommodation_adr, 0)) rev_bk,
 sum(if(occupancy>0, accommodation_adr, 0)) rev_tot
from `views.listing_daily_stats` s where availability=1 and date between '2024-01-01' and '2026-10-31' group by 1,2);
