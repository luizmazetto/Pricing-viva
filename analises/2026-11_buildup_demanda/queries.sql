-- historico_predio_mes.psv (header: b|m|n|rev|mrevpar|rev_air|rev_bk|rev_tot|n_mkt) · Metabase database 7 (BigQuery)
select string_agg(format('%s|%s|%d|%.4f|%s|%.0f|%.0f|%.0f|%d', b, m, n, rev, coalesce(format('%.4f', mrevpar),''), rev_air, rev_bk, rev_tot, n_mkt), '\n' order by b, m) from (
select s.buildingName b, format_date('%Y-%m', date) m, count(*) n, avg(coalesce(accommodation_adr,0)) rev,
 avg(if(market_occupancy is not null and market_median_booked_price is not null, market_median_booked_price*market_occupancy, null)) mrevpar,
 countif(market_occupancy is not null) n_mkt,
 sum(if(occupancy>0 and lower(reservation.source) like '%airbnb%', accommodation_adr, 0)) rev_air,
 sum(if(occupancy>0 and lower(reservation.source) like '%booking%', accommodation_adr, 0)) rev_bk,
 sum(if(occupancy>0, accommodation_adr, 0)) rev_tot
from `views.listing_daily_stats` s where availability=1 and date between '2024-01-01' and '2026-10-31' group by 1,2);

-- outros_canais_predio_mes.psv (header: b|m|out_mt|out_st|ota_mt|n_out_st): receita de outros canais mid-term (LOS 28+) e curta estadia
select string_agg(format('%s|%s|%.0f|%.0f|%.0f|%d', b, m, out_mt, out_st, ota_mt, n_out_st), '\n' order by b, m) from (
select s.buildingName b, format_date('%Y-%m', date) m,
 sum(if(occupancy>0 and not (lower(reservation.source) like '%airbnb%' or lower(reservation.source) like '%booking%') and reservation.los>=28, accommodation_adr, 0)) out_mt,
 sum(if(occupancy>0 and not (lower(reservation.source) like '%airbnb%' or lower(reservation.source) like '%booking%') and coalesce(reservation.los,0)<28, accommodation_adr, 0)) out_st,
 sum(if(occupancy>0 and (lower(reservation.source) like '%airbnb%' or lower(reservation.source) like '%booking%') and reservation.los>=28, accommodation_adr, 0)) ota_mt,
 countif(occupancy>0 and not (lower(reservation.source) like '%airbnb%' or lower(reservation.source) like '%booking%') and coalesce(reservation.los,0)<28) n_out_st
from `views.listing_daily_stats` s where availability=1 and date between '2024-11-01' and '2026-10-31' group by 1,2);

-- expedia_receita_predio_mes.psv (header: b|m|rev_exp)
select string_agg(format('%s|%s|%.0f', b, m, rev_exp), '\n' order by b, m) from (
select s.buildingName b, format_date('%Y-%m', date) m,
 sum(if(occupancy>0 and lower(coalesce(reservation.source,'')) like '%expedia%', accommodation_adr, 0)) rev_exp
from `views.listing_daily_stats` s where availability=1 and date between '2024-01-01' and '2026-10-31' group by 1,2);

-- reviews_expedia_predio_mes.psv (header: b|m|n|sg|mn|mx): nota 1–5
select string_agg(format('%s|%s|%d|%.1f|%.1f|%.1f', b, m, n, sg, mn, mx), '\n' order by b, m) from (
select l.buildingName b, format_date('%Y-%m', date(rev.createdAt)) m, count(*) n, sum(rev.general) sg, min(rev.general) mn, max(rev.general) mx
from replicas.vivadb_review rev join replicas.vivadb_reservation res on rev.idreserve=res.id_ join replicas.vivadb_listing l on l.id_=res.idlisting
where lower(res.partnerName) like '%expedia%' and rev.general > 0 and l.buildingName is not null and date(rev.createdAt) <= '2026-10-31' group by 1,2);
