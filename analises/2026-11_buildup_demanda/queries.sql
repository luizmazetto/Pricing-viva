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

-- metabase_unidade_jul_set26.psv (header: u;m;disp;dia;rev): diárias por unidade para o ajuste de ago/26 da Report DB
select internalName u, format_date('%Y-%m', date) m, countif(availability=1) disp, countif(availability=1 and occupancy>0) dia,
 sum(if(availability=1 and occupancy>0, accommodation_adr, 0)) rev
from `views.listing_daily_stats` where date between '2026-07-01' and '2026-09-30'
 and regexp_contains(internalName, r'^(NXP 950|NXF 444|NUN 61|PQJ 155|KAS 99) ') group by 1,2;

-- Taxa efetiva de comissão por canal (Premissas, item 10): check-in mai–set/26
select case when lower(r.partnerName) like '%airbnb%' then 'air' when lower(r.partnerName) like '%booking%' then 'bk' when lower(r.partnerName) like '%expedia%' then 'exp' else 'out' end ch,
 count(*) n, sum(r.commissionValue)/sum(safe_cast(json_value(r.price,'$._f_total') as float64)) taxa
from replicas.vivadb_reservation r join replicas.vivadb_listing l on l.id_ = r.idlisting
where r.checkInDate >= '2026-05-01' and r.checkInDate < '2026-10-01' and r.type not in ('blocked','maintenance') and l.buildingName is not null and l.buildingName not like 'ZZZ%'
group by 1;

-- metabase_reservas_unidade_mai_set26.psv (u;m;n_overlap;n_checkin;n_checkout;nights): n_overlap = definição da Report DB
select internalName u, format_date('%Y-%m', date) m, count(distinct if(occupancy>0, reservation.id, null)) n_overlap,
 count(distinct if(occupancy>0 and format_date('%Y-%m', reservation.checkin)=format_date('%Y-%m', date), reservation.id, null)) n_checkin,
 count(distinct if(occupancy>0 and format_date('%Y-%m', date_sub(reservation.checkout, interval 1 day))=format_date('%Y-%m', date), reservation.id, null)) n_checkout,
 countif(occupancy>0) nights
from `views.listing_daily_stats` where date between '2026-05-01' and '2026-09-30' and availability=1 and internalName is not null group by 1,2;

-- demais_direto_outros_jul_out26.psv (b|rev_tot|rev_dir|rev_out): receita de hospedagem jul–out/26, canal direto vs outros canais
select s.buildingName b, sum(if(occupancy>0, accommodation_adr, 0)) rev_tot,
 sum(if(occupancy>0 and regexp_contains(lower(coalesce(reservation.source,'')), r'^0\. direct|^direct|extens|website|reserva interna'), accommodation_adr, 0)) rev_dir,
 sum(if(occupancy>0 and not regexp_contains(lower(coalesce(reservation.source,'')), r'airbnb|booking|expedia|^0\. direct|^direct|extens|website|reserva interna'), accommodation_adr, 0)) rev_out
from `views.listing_daily_stats` s where availability=1 and date between '2026-07-01' and '2026-10-31' group by 1;
