"""Load earthquake_features.parquet + graph_a_metrics.csv into the dockerized Postgres.

Usage:
    docker compose up -d postgres
    python3 scripts/load_to_postgres.py
"""
import io
import sys
from pathlib import Path

import pandas as pd
import psycopg2

import os

ROOT = Path(__file__).resolve().parent.parent
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "55432")
PG_DB = os.getenv("POSTGRES_DB", "gempa")
PG_USER = os.getenv("POSTGRES_USER", "gempa")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "changeme")

DSN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} user={PG_USER} password={PG_PASS}"

EVENTS_COLUMNS = [
    "event_id", "source", "time_utc", "mag", "mag_type", "depth_km",
    "latitude", "longitude", "place", "tsunami", "sig", "mmi", "cdi",
    "felt", "gap", "dmin", "rms", "nst", "year", "month",
    "cross_validated", "sig_estimated", "depth_class", "mag_band", "zone_id",
]

SCHEMA_SQL = """
DROP TABLE IF EXISTS earthquake_events;
CREATE TABLE earthquake_events (
    event_id text PRIMARY KEY,
    source text,
    time_utc timestamptz NOT NULL,
    mag double precision,
    mag_type text,
    depth_km double precision,
    latitude double precision,
    longitude double precision,
    place text,
    tsunami smallint,
    sig double precision,
    mmi double precision,
    cdi double precision,
    felt double precision,
    gap double precision,
    dmin double precision,
    rms double precision,
    nst double precision,
    year int,
    month int,
    cross_validated boolean,
    sig_estimated smallint,
    depth_class text,
    mag_band text,
    zone_id text,
    geom geometry(Point, 4326)
);
CREATE INDEX idx_events_time ON earthquake_events (time_utc);
CREATE INDEX idx_events_zone ON earthquake_events (zone_id);
CREATE INDEX idx_events_geom ON earthquake_events USING gist (geom);

DROP TABLE IF EXISTS zone_metrics;
CREATE TABLE zone_metrics (
    zone_id text PRIMARY KEY,
    degree int,
    betweenness double precision,
    eigenvector double precision,
    pagerank double precision
);
"""


def load_events(conn) -> int:
    df = pd.read_parquet(ROOT / "data/processed/earthquake_features.parquet")
    df = df[EVENTS_COLUMNS].copy()
    df["depth_class"] = df["depth_class"].astype(str)
    df["mag_band"] = df["mag_band"].astype(str)

    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)

    with conn.cursor() as cur:
        cur.copy_expert(
            f"COPY earthquake_events ({', '.join(EVENTS_COLUMNS)}) FROM STDIN WITH CSV NULL '\\N'",
            buf,
        )
        cur.execute(
            "UPDATE earthquake_events SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)"
        )
    conn.commit()
    return len(df)


def load_zone_metrics(conn) -> int:
    df = pd.read_csv(ROOT / "data/processed/graph_a_metrics.csv")
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    buf.seek(0)
    with conn.cursor() as cur:
        cur.copy_expert(
            "COPY zone_metrics (zone_id, degree, betweenness, eigenvector, pagerank) FROM STDIN WITH CSV",
            buf,
        )
    conn.commit()
    return len(df)


def main():
    conn = psycopg2.connect(DSN)
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        conn.commit()

        n_events = load_events(conn)
        n_zones = load_zone_metrics(conn)
        print(f"Loaded {n_events} events and {n_zones} zone metrics into Postgres.")
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
