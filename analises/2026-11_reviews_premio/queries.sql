-- Extração de 18/nov/2026 (Metabase execute_sql, database 7 = BigQuery). Cada query devolve uma string pipe-separated.

-- q1 · data/reviews_master_month.psv  (header: master|b|m|n|sg|n5|n3|scl|slo|sva|sac|sci|sco|nsub)
with r as (
select coalesce(l.idCloneGroupMaster, l.id_) master_id, l.buildingName b, format_date('%Y-%m', date(rev.createdAt)) m,
  rev.general g, rev.cleaning cl, rev.location lo, rev.value va, rev.accuracy ac, rev.checkin ci, rev.communication co
from replicas.vivadb_review rev join replicas.vivadb_reservation res on rev.idreserve=res.id_
join replicas.vivadb_listing l on l.id_=res.idlisting
where res.partnerName like '%airbnb%' and rev.general > 0 and l.buildingName is not null and l.buildingName not like '%ZZZ%' and date(rev.createdAt) <= '2026-11-17')
select string_agg(format('%s|%s|%s|%d|%.1f|%d|%d|%.1f|%.1f|%.1f|%.1f|%.1f|%.1f|%d', master_id, b, m, n, sg, n5, n3, scl, slo, sva, sac, sci, sco, nsub), '\n' order by b, master_id, m) from (
select master_id, b, m, count(*) n, sum(g) sg, countif(g=5) n5, countif(g<=3) n3,
 sum(if(cl>0,cl,null)) scl, sum(if(lo>0,lo,null)) slo, sum(if(va>0,va,null)) sva, sum(if(ac>0,ac,null)) sac, sum(if(ci>0,ci,null)) sci, sum(if(co>0,co,null)) sco,
 countif(cl>0 and lo>0 and va>0 and ac>0 and ci>0 and co>0) nsub
from r group by 1,2,3);

-- q2 · data/reviews_booking_master_month.psv  (header: master|b|m|n|sg) — nota Booking em 0–10 (general × 2)
select string_agg(format('%s|%s|%s|%d|%.1f', master_id, b, m, n, sg), '\n' order by b, master_id, m) from (
select coalesce(l.idCloneGroupMaster, l.id_) master_id, l.buildingName b, format_date('%Y-%m', date(rev.createdAt)) m, count(*) n, sum(rev.general*2) sg
from replicas.vivadb_review rev join replicas.vivadb_reservation res on rev.idreserve=res.id_ join replicas.vivadb_listing l on l.id_=res.idlisting
where res.partnerName like '%booking%' and rev.general > 0 and l.buildingName is not null and date(rev.createdAt) <= '2026-11-17' group by 1,2,3);

-- q3 · data/premio_master_month.psv  (header: master|b|m|n|rev|mrevpar|occ|mo|occ_mt)
select string_agg(format('%s|%s|%s|%d|%.2f|%.2f|%.4f|%.4f|%.4f', master_id, b, m, n, rev, mrevpar, occ, mo, occ_mt), '\n' order by b, master_id, m) from (
select master_id, s.buildingName b, format_date('%Y-%m', date) m, count(*) n, avg(coalesce(accommodation_adr,0)) rev,
 avg(market_median_booked_price*market_occupancy) mrevpar, avg(occupancy) occ, avg(market_occupancy) mo, avg(if(occupancy>0 and reservation.los>=28,1,0)) occ_mt
from `views.listing_daily_stats` s where availability=1 and date between '2024-11-01' and '2026-10-31' group by 1,2,3);

-- q4 · data/canal_master_month.psv  (header: master|b|m|n_airbnb|rev_airbnb|rev_booking|n_booking|rev_total|n_booked)
select string_agg(format('%s|%s|%s|%d|%.0f|%.0f|%d|%.0f|%d', master_id, b, m, n_airbnb, rev_airbnb, rev_booking, n_booking, rev_total, n_booked), '\n' order by b, master_id, m) from (
select master_id, s.buildingName b, format_date('%Y-%m', date) m,
 countif(occupancy>0 and reservation.source like '%airbnb%') n_airbnb, sum(if(occupancy>0 and reservation.source like '%airbnb%', accommodation_adr, 0)) rev_airbnb,
 countif(occupancy>0 and reservation.source like '%booking%') n_booking, sum(if(occupancy>0 and reservation.source like '%booking%', accommodation_adr, 0)) rev_booking,
 sum(if(occupancy>0, accommodation_adr, 0)) rev_total, countif(occupancy>0) n_booked
from `views.listing_daily_stats` s where availability=1 and date between '2024-11-01' and '2026-10-31' group by 1,2,3);
