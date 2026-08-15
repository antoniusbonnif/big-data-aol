"""Near Real-Time Earthquake Stream Ingestion Worker.

Polls USGS & BMKG live feeds, processes spatial features, and streams new events
directly into PostgreSQL/PostGIS.

Usage:
    python3 scripts/stream_worker.py
"""
import logging
import os
import sys
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

import numpy as np
import pandas as pd
import psycopg2
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("stream_worker")

# Configuration
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "55432")
PG_DB = os.getenv("POSTGRES_DB", "gempa")
PG_USER = os.getenv("POSTGRES_USER", "gempa")
PG_PASS = os.getenv("POSTGRES_PASSWORD", "changeme")
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "60"))

DSN = f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} user={PG_USER} password={PG_PASS}"

USGS_ALL_DAY_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
BMKG_AUTOGEMPA_URL = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"
BMKG_TERKINI_URL = "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json"

BBOX = {"minlat": -11.0, "maxlat": 6.0, "minlon": 95.0, "maxlon": 141.0}
EXCLUDE_KEYWORDS = ["Philippines", "Timor Leste", "Malaysia", "Papua New Guinea", "Australia"]


def get_db_connection():
    return psycopg2.connect(DSN)


def is_in_indonesia(lat: float, lon: float, place: str) -> bool:
    if not (BBOX["minlat"] <= lat <= BBOX["maxlat"] and BBOX["minlon"] <= lon <= BBOX["maxlon"]):
        return False
    place_lower = (place or "").lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw.lower() in place_lower:
            return False
    return True


def assign_bins(lat: float, lon: float, depth_km: float, mag: float) -> tuple:
    # depth_class
    if depth_km <= 70:
        depth_class = "shallow"
    elif depth_km <= 300:
        depth_class = "intermediate"
    else:
        depth_class = "deep"

    # mag_band
    if mag <= 4.5:
        mag_band = "4.0-4.5"
    elif mag <= 5.5:
        mag_band = "4.5-5.5"
    elif mag <= 6.5:
        mag_band = "5.5-6.5"
    else:
        mag_band = "6.5+"

    zone_lat = int(lat // 1)
    zone_lon = int(lon // 1)
    zone_id = f"{zone_lat}_{zone_lon}"

    return depth_class, mag_band, zone_id


def fetch_usgs_live() -> List[Dict[str, Any]]:
    events = []
    try:
        resp = requests.get(USGS_ALL_DAY_URL, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for feat in data.get("features", []):
                props = feat.get("properties", {})
                coords = feat.get("geometry", {}).get("coordinates", [])
                if len(coords) < 3:
                    continue
                lon, lat, depth = float(coords[0]), float(coords[1]), float(coords[2])
                place = props.get("place") or ""
                mag = props.get("mag")
                if mag is None:
                    continue
                mag = float(mag)

                if not is_in_indonesia(lat, lon, place):
                    continue

                event_id = str(feat["id"])
                time_epoch_ms = props.get("time")
                if time_epoch_ms:
                    time_utc = datetime.fromtimestamp(time_epoch_ms / 1000.0, tz=timezone.utc)
                else:
                    time_utc = datetime.now(timezone.utc)

                depth_class, mag_band, zone_id = assign_bins(lat, lon, depth, mag)
                sig = props.get("sig")
                if sig is None:
                    sig = 10.0 * (mag ** 2)

                events.append({
                    "event_id": event_id,
                    "source": "usgs",
                    "time_utc": time_utc,
                    "mag": mag,
                    "mag_type": props.get("magType") or "unknown",
                    "depth_km": depth,
                    "latitude": lat,
                    "longitude": lon,
                    "place": place,
                    "tsunami": int(props.get("tsunami") or 0),
                    "sig": float(sig),
                    "mmi": float(props.get("mmi") or -1),
                    "cdi": float(props.get("cdi") or -1),
                    "felt": float(props.get("felt") or -1),
                    "gap": float(props.get("gap") or 180),
                    "dmin": float(props.get("dmin") or 1.0),
                    "rms": float(props.get("rms") or 0.8),
                    "nst": float(props.get("nst") or 20),
                    "year": time_utc.year,
                    "month": time_utc.month,
                    "cross_validated": False,
                    "sig_estimated": 0 if props.get("sig") is not None else 1,
                    "depth_class": depth_class,
                    "mag_band": mag_band,
                    "zone_id": zone_id,
                })
    except Exception as e:
        logger.warning(f"Error fetching USGS live feed: {e}")
    return events


def fetch_bmkg_live() -> List[Dict[str, Any]]:
    events = []
    urls = [BMKG_AUTOGEMPA_URL, BMKG_TERKINI_URL]
    for url in urls:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                continue
            data = resp.json()
            info_gempa = data.get("Infogempa", {}).get("gempa", [])
            if isinstance(info_gempa, dict):
                info_gempa = [info_gempa]

            for ev in info_gempa:
                lintang_str = ev.get("Lintang", "")
                bujur_str = ev.get("Bujur", "")
                if not lintang_str or not bujur_str:
                    continue

                lat_val = float(lintang_str.split()[0]) * (-1 if "LS" in lintang_str else 1)
                lon_val = float(bujur_str.split()[0]) * (-1 if "BB" in bujur_str else 1)
                depth_str = ev.get("Kedalaman", "10 km")
                depth_km = float(re.sub(r"[^\d.]", "", depth_str) or 10.0)
                mag = float(ev.get("Magnitude", 4.0))
                place = ev.get("Wilayah", "")
                potensi = ev.get("Potensi", "").lower()
                tsunami = 1 if "berpotensi" in potensi and "tidak" not in potensi else 0

                if not is_in_indonesia(lat_val, lon_val, place):
                    continue

                date_time_str = ev.get("DateTime")
                if date_time_str:
                    time_utc = pd.to_datetime(date_time_str, utc=True).to_pydatetime()
                else:
                    time_utc = datetime.now(timezone.utc)

                event_id = f"bmkg_{date_time_str or time_utc.isoformat()}"
                depth_class, mag_band, zone_id = assign_bins(lat_val, lon_val, depth_km, mag)
                sig = 10.0 * (mag ** 2)

                events.append({
                    "event_id": event_id,
                    "source": "bmkg",
                    "time_utc": time_utc,
                    "mag": mag,
                    "mag_type": "unknown",
                    "depth_km": depth_km,
                    "latitude": lat_val,
                    "longitude": lon_val,
                    "place": place,
                    "tsunami": tsunami,
                    "sig": sig,
                    "mmi": -1.0,
                    "cdi": -1.0,
                    "felt": -1.0,
                    "gap": 180.0,
                    "dmin": 1.0,
                    "rms": 0.8,
                    "nst": 20.0,
                    "year": time_utc.year,
                    "month": time_utc.month,
                    "cross_validated": False,
                    "sig_estimated": 1,
                    "depth_class": depth_class,
                    "mag_band": mag_band,
                    "zone_id": zone_id,
                })
        except Exception as e:
            logger.warning(f"Error fetching BMKG live feed from {url}: {e}")
    return events


INSERT_SQL = """
INSERT INTO earthquake_events (
    event_id, source, time_utc, mag, mag_type, depth_km,
    latitude, longitude, place, tsunami, sig, mmi, cdi,
    felt, gap, dmin, rms, nst, year, month,
    cross_validated, sig_estimated, depth_class, mag_band, zone_id,
    geom
) VALUES (
    %(event_id)s, %(source)s, %(time_utc)s, %(mag)s, %(mag_type)s, %(depth_km)s,
    %(latitude)s, %(longitude)s, %(place)s, %(tsunami)s, %(sig)s, %(mmi)s, %(cdi)s,
    %(felt)s, %(gap)s, %(dmin)s, %(rms)s, %(nst)s, %(year)s, %(month)s,
    %(cross_validated)s, %(sig_estimated)s, %(depth_class)s, %(mag_band)s, %(zone_id)s,
    ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)
) ON CONFLICT (event_id) DO NOTHING;
"""


def upsert_events(events: List[Dict[str, Any]]) -> int:
    if not events:
        return 0

    inserted_count = 0
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            for ev in events:
                cur.execute(INSERT_SQL, ev)
                if cur.rowcount > 0:
                    inserted_count += cur.rowcount
                    logger.info(f"✨ NEW EVENT: [{ev['source'].upper()}] M{ev['mag']} at {ev['place']} ({ev['time_utc']}) - Zone: {ev['zone_id']}")
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Failed to upsert events to Postgres: {e}")
    finally:
        if conn:
            conn.close()

    return inserted_count


def run_worker_loop():
    logger.info("==================================================")
    logger.info("🌍 Earthquake Live Streaming Ingestion Worker")
    logger.info(f"Target Postgres: {PG_HOST}:{PG_PORT}/{PG_DB}")
    logger.info(f"Poll Interval: {POLL_INTERVAL_SEC}s")
    logger.info("==================================================")

    while True:
        try:
            usgs_events = fetch_usgs_live()
            bmkg_events = fetch_bmkg_live()
            all_events = usgs_events + bmkg_events

            new_count = upsert_events(all_events)
            if new_count > 0:
                logger.info(f"Successfully processed {len(all_events)} live events ({new_count} new events inserted).")
            else:
                logger.debug(f"Heartbeat: {len(all_events)} events checked. No new events.")

        except Exception as e:
            logger.error(f"Unexpected error in streaming loop: {e}")

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    run_worker_loop()
