-- Extração de 13/out/2026, Metabase database 6 (Postgres), tabela "Calendar".
-- Ocupação sem mid-term: estadia >= 28 noites sai do numerador e do denominador; blocked/maintenance não contam.

-- q1 · data/now_23_24.psv
with c as (
 select city, "buildingName" b, "date"::date d, idlisting, status::text st, los, "creationDate"::date cd, "dailyRate" rate,
  listing_prices_price pl, listing_prices_min_stay ms, mkt_occ, mkt_price,
  (status::text in ('available','booked') and not (status::text='booked' and los>=28)) st_ok
 from "Calendar" where coalesce(deleted,false)=false and "date"::date in ('2026-10-02','2026-10-03','2026-10-23','2026-10-24','2026-10-25')
)
select city, b,
 count(distinct idlisting) filter (where d in ('2026-10-23','2026-10-24')) units,
 count(*) filter (where d in ('2026-10-23','2026-10-24') and st_ok) n_st,
 count(*) filter (where d in ('2026-10-23','2026-10-24') and st_ok and st='booked') bk_st,
 count(*) filter (where d in ('2026-10-23','2026-10-24') and st='booked' and los>=28) bk_mt,
 count(*) filter (where d in ('2026-10-23','2026-10-24') and st='available') free_n,
 count(*) filter (where d in ('2026-10-23','2026-10-24') and st='booked' and los<28 and cd>='2026-10-06') bk_l7,
 round(avg(pl) filter (where d in ('2026-10-23','2026-10-24') and st='available')::numeric,0) ask,
 round(avg(rate) filter (where d in ('2026-10-23','2026-10-24') and st='booked' and los<28)::numeric,0) adr,
 round(avg(ms) filter (where d in ('2026-10-23','2026-10-24') and st='available')::numeric,1) min_stay,
 round(avg(mkt_occ) filter (where d in ('2026-10-23','2026-10-24'))::numeric,1) mkt_occ,
 round(avg(mkt_price) filter (where d in ('2026-10-23','2026-10-24'))::numeric,0) mkt_price,
 count(*) filter (where d='2026-10-25' and st_ok) n25, count(*) filter (where d='2026-10-25' and st_ok and st='booked') bk25,
 count(*) filter (where d in ('2026-10-02','2026-10-03') and st_ok) n_r1,
 count(*) filter (where d in ('2026-10-02','2026-10-03') and st_ok and st='booked') bk_r1,
 round(avg(mkt_occ) filter (where d in ('2026-10-02','2026-10-03'))::numeric,1) mkt_r1
from c group by 1,2 order by 1,2;

-- q2 · data/base_weekends.psv (pace em T-10 para sexta e T-11 para sábado; mercado em T-10.5 interpolado entre pre_14 e pre_7)
select city, "buildingName" b,
 count(*) filter (where status::text in ('available','booked') and not (status::text='booked' and los>=28)) n_st,
 round(avg(case when status::text='booked' and los<28 and "creationDate"::date <= "date"::date - (case when extract(dow from "date"::date)=5 then 10 else 11 end) then 1.0 else 0 end) filter (where status::text in ('available','booked') and not (status::text='booked' and los>=28)),3) pace,
 round(avg(case when status::text='booked' and los<28 then 1.0 else 0 end) filter (where status::text in ('available','booked') and not (status::text='booked' and los>=28)),3) fin,
 round(avg("dailyRate") filter (where status::text='booked' and los<28)::numeric,0) adr,
 round(avg(mkt_occ_pre_14 + (mkt_occ_pre_7-mkt_occ_pre_14)*0.5)::numeric,1) mkt_t10, round(avg(mkt_occ)::numeric,1) mkt_fin
from "Calendar" where coalesce(deleted,false)=false and "date"::date between '2026-08-01' and '2026-10-03' and extract(dow from "date"::date) in (5,6)
group by 1,2 order by 1,2;

-- q3 · data/city_weekends.psv (troque o intervalo de datas para 2024-10-04..2024-11-16 para a série de 2024)
select city, "date"::date d,
 count(*) filter (where status::text in ('available','booked') and not (status::text='booked' and los>=28)) n_st,
 round(avg(case when status::text='booked' and los<28 then 1.0 else 0 end) filter (where status::text in ('available','booked') and not (status::text='booked' and los>=28)),3) fin,
 round(avg(case when status::text='booked' and los<28 and "creationDate"::date <= "date"::date - (case when extract(dow from "date"::date)=5 then 10 else 11 end) then 1.0 else 0 end) filter (where status::text in ('available','booked') and not (status::text='booked' and los>=28)),3) pace_t10,
 round(avg(mkt_occ)::numeric,1) mkt, round(avg(mkt_occ_pre_14 + (mkt_occ_pre_7-mkt_occ_pre_14)*0.5)::numeric,1) mkt_t10
from "Calendar" where coalesce(deleted,false)=false and city in ('São Paulo','Florianópolis')
 and "date"::date between '2026-09-11' and '2026-10-31' and extract(dow from "date"::date) in (5,6)
group by 1,2 order by 1,2;
