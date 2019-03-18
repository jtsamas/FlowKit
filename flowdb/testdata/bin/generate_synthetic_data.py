# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#!/usr/bin/env python

"""
Small script for generating arbitrary volumes of CDR call data inside the flowdb
container. Produces csvs containing cell infrastructure data, and CDR call data,
together with SQL to ingest these CSVs, based on the SQL template found in
../synthetic_data/sql

Cell data is generated from a GeoJSON file with (simplified) admin3 boundaries for
Nepal found in ../synthetic_data/data/NPL_admbnda_adm3_Districts_simplified.geojson

Makes use of the tohu module for generation of random data.
"""

import os
import argparse
import datetime
from concurrent.futures.thread import ThreadPoolExecutor
from multiprocessing import cpu_count

import sqlalchemy as sqlalchemy

parser = argparse.ArgumentParser(description="Flowminder Synthetic CDR Generator\n")
parser.add_argument(
    "--n-subscribers", type=int, default=4000, help="Number of subscribers to generate."
)
parser.add_argument(
    "--n-tacs", type=int, default=4000, help="Number of phone models to generate."
)
parser.add_argument(
    "--n-sites", type=int, default=1000, help="Number of sites to generate."
)
parser.add_argument(
    "--n-cells", type=int, default=1000, help="Number of cells to generate."
)
parser.add_argument(
    "--n-calls", type=int, default=200_000, help="Number of calls to generate per day."
)
parser.add_argument(
    "--n-sms", type=int, default=200_000, help="Number of sms to generate per day."
)
parser.add_argument(
    "--n-mds", type=int, default=200_000, help="Number of mds to generate per day."
)
parser.add_argument(
    "--n-days", type=int, default=7, help="Number of days of data to generate."
)
parser.add_argument(
    "--cluster", action="store_true", help="Cluster tables on msisdn index."
)
parser.add_argument(
    "--disaster-zone",
    default=False,
    type=str,
    help="Admin 2 pcod to use as disaster zone.",
)
parser.add_argument(
    "--disaster-start-date",
    type=datetime.date.fromisoformat,
    help="Date to begin the disaster.",
)
parser.add_argument(
    "--disaster-end-date",
    type=datetime.date.fromisoformat,
    help="Date to end the disaster.",
)
parser.add_argument(
    "--output-root-dir",
    type=str,
    default="",
    help="Root directory under which output .sql is stored (in appropriate subfolders).",
)


if __name__ == "__main__":
    print("Generating synthetic data..")
    args = parser.parse_args()
    print(args)
    num_subscribers = args.n_subscribers
    num_sites = args.n_sites
    num_cells = args.n_cells
    num_calls = args.n_calls
    num_sms = args.n_sms
    num_mds = args.n_mds
    num_days = args.n_days
    num_tacs = args.n_tacs
    pcode_to_knock_out = args.disaster_zone
    try:
        disaster_start_date = args.disaster_start_date
    except AttributeError:
        disaster_start_date = False
        pass  # No disaster
    try:
        disaster_end_date = args.disaster_end_date
    except AttributeError:
        disaster_end_date = datetime.date(2016, 1, 1) + datetime.timedelta(
            days=num_days
        )

    engine = sqlalchemy.create_engine(
        f"postgresql://{os.getenv('POSTGRES_USER')}@/{os.getenv('POSTGRES_DB')}",
        echo=False,
        strategy="threadlocal",
        pool_size=cpu_count(),
        pool_timeout=None,
    )

    start_time = datetime.datetime.now()

    with engine.begin() as trans:
        print(f"Generating {num_sites} sites.")
        start = datetime.datetime.now()
        trans.execute(
            f"""CREATE TEMPORARY TABLE tmp_sites as 
        select row_number() over() as rid, md5(uuid_generate_v4()::text) as id, 
        0 as version, (date '2015-01-01' + random() * interval '1 year')::date as date_of_first_service,
        (p).geom as geom_point from (select st_dumppoints(ST_GeneratePoints(geom, {num_sites})) as p from geography.admin0) _;"""
        )
        trans.execute(
            "INSERT INTO infrastructure.sites (id, version, date_of_first_service, geom_point) SELECT id, version, date_of_first_service, geom_point FROM tmp_sites;"
        )
        print(f"Done. Runtime: {datetime.datetime.now() - start}")
        print(f"Generating {num_cells} cells.")
        start = datetime.datetime.now()
        trans.execute(
            f"""CREATE TABLE tmp_cells as
            SELECT row_number() over() as rid, *, -1 as rid_knockout FROM
            (select md5(uuid_generate_v4()::text) as id, version, tmp_sites.id as site_id, date_of_first_service, geom_point from tmp_sites
            union all
            select * from 
            (select md5(uuid_generate_v4()::text) as id, version, tmp_sites.id as site_id, date_of_first_service, geom_point from
            (
              select floor(random() * {num_sites} + 1)::integer as id
              from generate_series(1, {int(num_cells * 1.1)}) -- Preserve duplicates
            ) rands
            inner JOIN tmp_sites
            ON rands.id=tmp_sites.rid
            limit {num_cells - num_sites}) _) _;
            CREATE INDEX ON tmp_cells (rid);
            """
        )
        trans.execute(
            "INSERT INTO infrastructure.cells (id, version, site_id, date_of_first_service, geom_point) SELECT id, version, site_id, date_of_first_service, geom_point FROM tmp_cells;"
        )
        print(f"Done. Runtime: {datetime.datetime.now() - start}")
        print(f"Generating {num_tacs} tacs.")
        start = datetime.datetime.now()
        trans.execute(
            f"""create table tacs as
        (select row_number() over() as tac, 
        (ARRAY['Nokia', 'Huawei', 'Apple', 'Samsung', 'Sony', 'LG', 'Google', 'Xiaomi', 'ZTE'])[floor((random()*9 + 1))::int] as brand, 
        uuid_generate_v4()::text as model, 
        (ARRAY['Smart', 'Feature', 'Basic'])[floor((random()*3 + 1))::int] as  hnd_type 
        FROM generate_series(1, {num_tacs}));"""
        )
        trans.execute(
            "INSERT INTO infrastructure.tacs (id, brand, model, hnd_type) SELECT tac as id, brand, model, hnd_type FROM tacs;"
        )
        print(f"Done. Runtime: {datetime.datetime.now() - start}")
        print(f"Generating {num_subscribers} subscribers.")
        start = datetime.datetime.now()
        trans.execute(
            f"""
        create table subs as
        (select row_number() over() as id, md5(uuid_generate_v4()::text) as msisdn, md5(uuid_generate_v4()::text) as imei, 
        md5(uuid_generate_v4()::text) as imsi, floor(random() * {num_tacs} + 1)::integer as tac 
        FROM generate_series(1, {num_subscribers}));
        CREATE INDEX on subs (id);
        """
        )
        print(f"Done. Runtime: {datetime.datetime.now() - start}")

    print("Assigning subscriber home regions.")
    start = datetime.datetime.now()
    with engine.begin() as trans:
        trans.execute(
            f"""CREATE TABLE homes AS (
        SELECT h.*, cells FROM
        (SELECT '2016-01-01'::date as home_date, id, admin3pcod as home_id FROM (
        SELECT *, floor(random() * 75 + 1)::integer as admin_id FROM subs
        ) subscribers
        LEFT JOIN
        (SELECT row_number() over() as admin_id, admin3pcod FROM 
        geography.admin3
        ) geo
        ON geo.admin_id=subscribers.admin_id) h
        LEFT JOIN 
        (select admin3pcod, array_agg(rid) as cells FROM tmp_cells LEFT JOIN geography.admin3 ON ST_Within(geom_point, geom) GROUP BY admin3pcod) c
        ON admin3pcod=home_id
        )
        """
        )
        trans.execute("CREATE INDEX ON homes (id);")
        trans.execute("CREATE INDEX ON homes (home_date);")
        trans.execute("CREATE INDEX ON homes (home_date, id);")
    for date in (
        datetime.date(2016, 1, 2) + datetime.timedelta(days=i) for i in range(num_days)
    ):
        with engine.begin() as trans:
            if (
                pcode_to_knock_out
                and disaster_start_date
                and disaster_start_date <= date <= disaster_end_date
            ):
                trans.execute(
                    f"""INSERT INTO homes
                                        SELECT h.*, cells FROM
                                        (SELECT '{date.strftime(
                        "%Y-%m-%d")}'::date as home_date, id, CASE WHEN (random() > 0.99 OR home_id = ANY((array(select admin3.admin3pcod FROM geography.admin3 WHERE admin2pcod = '{pcode_to_knock_out}')))) THEN admin3pcod ELSE home_id END as home_id FROM (
                                        SELECT *, floor(random() * 74 + 1)::integer as admin_id FROM homes
                                        WHERE home_date='{(date - datetime.timedelta(days=1)).strftime(
                        "%Y-%m-%d")}'::date
                                        ) subscribers
                                        LEFT JOIN
                                        (SELECT row_number() over() as admin_id, admin3pcod FROM 
                                        geography.admin3
                                        WHERE admin2pcod!='{pcode_to_knock_out}'
                                        ) geo
                                        ON geo.admin_id=subscribers.admin_id) h
                                        LEFT JOIN 
                                                (select admin3pcod, array_agg(rid) as cells FROM tmp_cells LEFT JOIN geography.admin3 ON ST_Within(geom_point, geom) GROUP BY admin3pcod) c
                                                ON admin3pcod=home_id
                                        """
                )
            else:
                trans.execute(
                    f"""INSERT INTO homes
                        SELECT h.*, cells FROM
                        (SELECT '{date.strftime("%Y-%m-%d")}'::date as home_date, id, CASE WHEN (random() > 0.99) THEN admin3pcod ELSE home_id END as home_id FROM (
                        SELECT *, floor(random() * 75 + 1)::integer as admin_id FROM homes
                        WHERE home_date='{(date - datetime.timedelta(days=1)).strftime("%Y-%m-%d")}'::date
                        ) subscribers
                        LEFT JOIN
                        (SELECT row_number() over() as admin_id, admin3pcod FROM 
                        geography.admin3
                        ) geo
                        ON geo.admin_id=subscribers.admin_id) h
                        LEFT JOIN 
                                (select admin3pcod, array_agg(rid) as cells FROM tmp_cells LEFT JOIN geography.admin3 ON ST_Within(geom_point, geom) GROUP BY admin3pcod) c
                                ON admin3pcod=home_id
                        """
                )
    print(f"Done. Runtime: {datetime.datetime.now() - start}")

    with engine.begin() as trans:
        trans.execute(
            "CREATE TABLE available_cells AS (SELECT '2016-01-01'::date as day, array_agg(rid) FROM tmp_cells);"
        )

    print("Generating disaster.")
    for date in (
        datetime.date(2016, 1, 2) + datetime.timedelta(days=i) for i in range(num_days)
    ):
        with engine.begin() as trans:
            if (
                pcode_to_knock_out
                and disaster_start_date
                and disaster_start_date <= date <= disaster_end_date
            ):
                trans.execute(
                    f"""
                INSERT INTO available_cells SELECT '{date.strftime("%Y-%m-%d")}'::date, array_agg(tmp_cells.rid) as cells FROM tmp_cells INNER JOIN (SELECT * FROM geography.admin2 WHERE admin2pcod != '{pcode_to_knock_out}') _ ON ST_Within(geom_point, geom);
                """
                )
            else:
                trans.execute(
                    f"""
                            INSERT INTO available_cells SELECT '{date.strftime(
                    "%Y-%m-%d")}'::date, array_agg(tmp_cells.rid) as cells FROM tmp_cells;
                            """
                )
    with engine.begin() as trans:
        trans.execute("CREATE INDEX ON available_cells (day);")

    if pcode_to_knock_out:
        print("Marking cells to knock out.")
        start = datetime.datetime.now()
        with engine.begin() as trans:
            trans.execute(
                f"""
            WITH renumber AS (SELECT tmp_cells.*, ROW_NUMBER() OVER() AS rn FROM tmp_cells INNER JOIN (SELECT * FROM geography.admin2 WHERE admin2pcod != '{pcode_to_knock_out}') _ ON ST_Within(geom_point, geom))
            UPDATE tmp_cells SET rid_knockout = (SELECT rn FROM renumber WHERE renumber.rid = tmp_cells.rid);
            """
            )
            trans.execute("CREATE INDEX ON tmp_cells (rid_knockout);")
            number_of_not_knocked_out_cells = trans.execute(
                "SELECT count(*) FROM tmp_cells WHERE rid_knockout != -1;"
            ).first()[0]
            print(f"{number_of_not_knocked_out_cells}/{num_cells} available.")
            print(f"Done. Runtime: {datetime.datetime.now() - start}")

    with engine.begin() as trans:
        for sub in ("calls", "sms", "mds"):
            if getattr(args, f"n_{sub}") > 0:
                for date in (
                    datetime.date(2016, 1, 1) + datetime.timedelta(days=i)
                    for i in range(num_days)
                ):
                    table = date.strftime("%Y%m%d")
                    end_date = (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                    print(f"Creating bare table for events.{sub}_{table}.")
                    engine.execute(
                        f"""
                    CREATE TABLE IF NOT EXISTS events.{sub}_{table} (
                                        CHECK ( datetime >= '{table}'::TIMESTAMPTZ
                                        AND datetime < '{end_date}'::TIMESTAMPTZ)
                                    ) INHERITS (events.{sub});
        
                    ALTER TABLE events.{sub}_{table} NO INHERIT events.{sub};"""
                    )

    sql = []
    for date in (
        datetime.date(2016, 1, 1) + datetime.timedelta(days=i) for i in range(num_days)
    ):
        table = date.strftime("%Y%m%d")
        end_date = (date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

        # calls
        if num_calls > 0:
            sql.append(
                (
                    f"Generating {num_calls} calls for {date}.",
                    f"""
            WITH interactions as 
            (SELECT uuid_generate_v4()::text as id, caller.msisdn as caller_msisdn, 
            caller.tac as caller_tac, caller.imsi as caller_imsi, caller.imei as caller_imei, 
            callee.msisdn as callee_msisdn, callee.tac as callee_tac, 
            callee.imsi as callee_imsi, callee.imei as callee_imei, 
            floor(random() * array_length(caller_cells, 1) + 1) as caller_cell, 
            floor(random() * array_length(callee_cells, 1) + 1) as callee_cell,
             (date '{table}' + random() * interval '1 day') as start_time
             FROM
            (
                SELECT 
                floor(random() * (select count(*) from subs) + 1)::integer as caller_id, 
                floor(random() * (select count(*) from subs) + 1)::integer as callee_id FROM 
                generate_series(1, {num_calls})) call_pairs
                LEFT JOIN 
                (SELECT id,
                    CASE WHEN (random() > 0.99) THEN
                        (SELECT cells FROM available_cells WHERE day='{table}'::date)
                    ELSE 
                        cells
                    END as caller_cells 
                    FROM homes WHERE home_date='{table}'::date) caller_homes
                ON call_pairs.caller_id=caller_homes.id
                LEFT JOIN 
                (SELECT id, 
                    CASE WHEN (random() > 0.99) THEN
                        (SELECT cells FROM available_cells WHERE day='{table}'::date)
                    ELSE 
                        cells
                    END as callee_cells  
                    FROM homes WHERE home_date='{table}'::date) callee_homes
                ON call_pairs.callee_id=callee_homes.id
                LEFT JOIN subs as caller ON call_pairs.caller_id = caller.id
                LEFT JOIN subs as callee ON call_pairs.callee_id = callee.id),
        
            calls as 
            (SELECT interactions.*,  
                round(random()*2600)::integer as duration FROM interactions)
        
            INSERT INTO events.calls_{table} (id, outgoing, duration, datetime, msisdn, tac, imsi, imei, location_id, msisdn_counterpart)
                SELECT two_lined_calls.id, outgoing, duration, datetime, msisdn, tac, imsi, imei,  tmp_cells.id, msisdn_counterpart FROM (
                    SELECT id, true as outgoing, duration, start_time as datetime, caller_msisdn as msisdn, caller_tac as tac, caller_imsi as imsi, caller_imei as imei, caller_cell as location_id, callee_msisdn as msisdn_counterpart 
                FROM calls
                UNION ALL
                SELECT id, false as outgoing, duration, start_time as datetime, callee_msisdn as msisdn, callee_tac as tac, callee_imsi as imsi, callee_imei as imei, callee_cell as location_id, caller_msisdn as msisdn_counterpart
                FROM calls) two_lined_calls
                LEFT JOIN tmp_cells
                ON tmp_cells.rid = two_lined_calls.location_id
                 ORDER BY datetime ASC, msisdn;
        
            CREATE INDEX ON events.calls_{table} (msisdn);
            CREATE INDEX ON events.calls_{table} (msisdn_counterpart);
            CREATE INDEX ON events.calls_{table} (tac);
            CREATE INDEX ON events.calls_{table} (location_id);
            CREATE INDEX ON events.calls_{table} (datetime);
            """,
                )
            )
        if num_sms > 0:
            sql.append(
                (
                    f"Generating {num_sms} sms for {date}.",
                    f"""
            WITH interactions as 
            (SELECT uuid_generate_v4()::text as id, caller.msisdn as caller_msisdn, 
            caller.tac as caller_tac, caller.imsi as caller_imsi, caller.imei as caller_imei, 
            callee.msisdn as callee_msisdn, callee.tac as callee_tac, 
            callee.imsi as callee_imsi, callee.imei as callee_imei, 
            floor(random() * array_length(caller_cells, 1) + 1) as caller_cell, 
            floor(random() * array_length(callee_cells, 1) + 1) as callee_cell,
            (date '{table}' + random() * interval '1 day') as start_time
             FROM
            (
                SELECT 
                floor(random() * (select count(*) from subs) + 1)::integer as caller_id, 
                floor(random() * (select count(*) from subs) + 1)::integer as callee_id FROM 
                generate_series(1, {num_sms})) call_pairs
                LEFT JOIN 
                (SELECT id,
                    CASE WHEN (random() > 0.99) THEN
                        (SELECT cells FROM available_cells WHERE day='{table}'::date)
                    ELSE 
                        cells
                    END as caller_cells 
                    FROM homes WHERE home_date='{table}'::date) caller_homes
                ON call_pairs.caller_id=caller_homes.id
                LEFT JOIN 
                (SELECT id, 
                    CASE WHEN (random() > 0.99) THEN
                        (SELECT cells FROM available_cells WHERE day='{table}'::date)
                    ELSE 
                        cells
                    END as callee_cells  
                    FROM homes WHERE home_date='{table}'::date) callee_homes
                ON call_pairs.callee_id=callee_homes.id
                LEFT JOIN subs as caller ON call_pairs.caller_id = caller.id
                LEFT JOIN subs as callee ON call_pairs.callee_id = callee.id)
     
            INSERT INTO events.sms_{table} (id, outgoing, datetime, msisdn, tac, imsi, imei, location_id, msisdn_counterpart)
    
            SELECT two_lined_sms.id, outgoing, datetime, msisdn, tac, imsi, imei, tmp_cells.id as location_id, msisdn_counterpart
            FROM
            (SELECT * FROM (SELECT id, true as outgoing, start_time as datetime, caller_msisdn as msisdn, caller_tac as tac, caller_imsi as imsi, caller_imei as imei, caller_cell as location_id, callee_msisdn as msisdn_counterpart
            FROM interactions
            UNION ALL
            SELECT id, false as outgoing, start_time as datetime, callee_msisdn as msisdn, callee_tac as tac, callee_imsi as imsi, callee_imei as imei, callee_cell as location_id, caller_msisdn as msisdn_counterpart
            FROM interactions) _ ORDER BY datetime ASC, msisdn) two_lined_sms
            LEFT JOIN tmp_cells
            ON tmp_cells.rid=two_lined_sms.location_id;
    
            CREATE INDEX ON events.sms_{table} (msisdn);
            CREATE INDEX ON events.sms_{table} (tac);
            CREATE INDEX ON events.sms_{table} (location_id);
            CREATE INDEX ON events.sms_{table} (datetime);
    
            """,
                )
            )
        if num_mds > 0:
            sql.append(
                (
                    f"Generating {num_mds} mds for {date}.",
                    f"""

            WITH interactions as 
            (SELECT caller.msisdn as msisdn, 
            caller.tac as tac, caller.imsi as imsi, caller.imei as imei, 
            floor(random() * array_length(caller_cells, 1) + 1) as caller_cell,
             (date '{table}' + random() * interval '1 day') as start_time
             FROM
            (
                SELECT 
                floor(random() * (select count(*) from subs) + 1)::integer as caller_id, 
                generate_series(1, {num_mds})) call_pairs
                LEFT JOIN 
                (SELECT id,
                    CASE WHEN (random() > 0.99) THEN
                        (SELECT cells FROM available_cells WHERE day='{table}'::date)
                    ELSE 
                        cells
                    END as caller_cells 
                    FROM homes WHERE home_date='{table}'::date) caller_homes
                ON call_pairs.caller_id=caller_homes.id
                LEFT JOIN subs as caller ON call_pairs.caller_id = caller.id
                )
            
            
            INSERT INTO events.mds_{table} (msisdn, tac, imsi, imei, volume_upload, volume_download, volume_total, location_id, datetime, duration)
            SELECT msisdn, tac, imsi, imei, volume_upload, volume_download, volume_total, location_id, datetime, duration FROM
            (SELECT msisdn, tac, imsi, imei, volume_upload, volume_download, 
            volume_upload + volume_download as volume_total, 
            tmp_cells.id as location_id, 
            (date '{table}' + random() * interval '1 day') as datetime, round(random() * 260)::integer as duration FROM
            (
                select *, floor(random() * {num_subscribers} + 1)::integer as id, round(random() * 100000)::integer as volume_upload, 
                round(random() * 100000)::integer as volume_download FROM interactions
                ) as mds
            LEFT JOIN tmp_cells
            ON tmp_cells.rid=mds.caller_cell
            ORDER BY datetime ASC, msisdn) _;
    
            CREATE INDEX ON events.mds_{table} (msisdn);
            CREATE INDEX ON events.mds_{table} (tac);
            CREATE INDEX ON events.mds_{table} (location_id);
            CREATE INDEX ON events.mds_{table} (datetime);
            """,
                )
            )

    post_sql = []
    attach_sql = []
    post_attach_sql = []
    for sub in ("calls", "sms", "mds"):
        if getattr(args, f"n_{sub}") > 0:
            for date in (
                datetime.date(2016, 1, 1) + datetime.timedelta(days=i)
                for i in range(num_days)
            ):
                table = date.strftime("%Y%m%d")
                attach_sql.append(
                    (
                        f"Attaching events.{sub}_{table}",
                        f"ALTER TABLE events.{sub}_{table} INHERIT events.{sub};",
                    )
                )
                if args.cluster:
                    post_sql.append(
                        (
                            f"Clustering events.{sub}_{table}.",
                            f"CLUSTER events.{sub}_{table} USING {sub}_{table}_msisdn_idx;",
                        )
                    )
                post_sql.append(
                    (
                        f"Analyzing events.{sub}_{table}",
                        f"ANALYZE events.{sub}_{table};",
                    )
                )
            post_sql.append(
                (
                    f"Updating availability for {sub}",
                    f"""
            INSERT INTO available_tables (table_name, has_locations, has_subscribers, has_counterparts) VALUES ('{sub}', true, true, true)
            ON conflict (table_name)
            DO UPDATE SET has_locations=EXCLUDED.has_locations, has_subscribers=EXCLUDED.has_subscribers, has_counterparts=EXCLUDED.has_counterparts;
            """,
                )
            )
        post_attach_sql.append((f"Analyzing {sub}", f"ANALYZE events.{sub};"))

    cleanup_sql = []
    for tbl in ("tmp_cells", "subs", "tacs", "available_cells", "homes"):
        cleanup_sql.append((f"Dropping {tbl}", f"DROP TABLE {tbl};"))

    def do_exec(args):
        msg, sql = args
        print(msg)
        started = datetime.datetime.now()
        with engine.begin() as trans:
            trans.execute(sql)
            print(f"Did: {msg}, runtime: {datetime.datetime.now() - started}")

    with ThreadPoolExecutor(cpu_count()) as tp:
        list(tp.map(do_exec, sql))
        list(tp.map(do_exec, post_sql))
    for s in attach_sql + cleanup_sql:
        do_exec(s)
    with ThreadPoolExecutor(cpu_count()) as tp:
        list(tp.map(do_exec, post_attach_sql))
    print(f"Total runtime: {datetime.datetime.now() - start_time}")
