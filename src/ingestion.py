"""Fungsi ingestion: USGS FDSN (gempa Indonesia) dan BMKG (gempa terkini)."""
import json
import time
from typing import Optional

import requests

USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_COUNT_URL = "https://earthquake.usgs.gov/fdsnws/event/1/count"
BMKG_GEMPATERKINI_URL = "https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json"
BMKG_AUTOGEMPA_URL = "https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json"

BBOX = dict(minlatitude=-11, maxlatitude=6, minlongitude=95, maxlongitude=141)
USGS_COUNT_LIMIT = 20000


def _get_with_retry(url: str, params: Optional[dict] = None, retries: int = 3, timeout: int = 30) -> requests.Response:
    """GET dengan retry backoff eksponensial. Raise di percobaan terakhir."""
    last_exc = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp
            last_exc = RuntimeError(f"HTTP {resp.status_code} for {url}")
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_exc = exc
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    raise last_exc


def usgs_count(starttime: str, endtime: str, min_magnitude: float = 4.0) -> int:
    params = dict(format="geojson", starttime=starttime, endtime=endtime,
                  minmagnitude=min_magnitude, **BBOX)
    resp = _get_with_retry(USGS_COUNT_URL, params)
    return resp.json()["count"]


def usgs_fetch(starttime: str, endtime: str, min_magnitude: float = 4.0) -> dict:
    params = dict(format="geojson", starttime=starttime, endtime=endtime,
                  minmagnitude=min_magnitude, **BBOX)
    resp = _get_with_retry(USGS_QUERY_URL, params)
    return resp.json()


def usgs_fetch_year(year: int, min_magnitude: float = 4.0) -> list:
    """Ambil event 1 tahun. Kalau count > limit, split per kuartal otomatis."""
    starttime, endtime = f"{year}-01-01", f"{year + 1}-01-01"
    count = usgs_count(starttime, endtime, min_magnitude)

    if count < USGS_COUNT_LIMIT:
        data = usgs_fetch(starttime, endtime, min_magnitude)
        return data["features"]

    quarters = [
        (f"{year}-01-01", f"{year}-04-01"),
        (f"{year}-04-01", f"{year}-07-01"),
        (f"{year}-07-01", f"{year}-10-01"),
        (f"{year}-10-01", f"{year + 1}-01-01"),
    ]
    features = []
    for q_start, q_end in quarters:
        data = usgs_fetch(q_start, q_end, min_magnitude)
        features.extend(data["features"])
    return features


def bmkg_fetch_gempaterkini() -> dict:
    resp = _get_with_retry(BMKG_GEMPATERKINI_URL)
    return resp.json()


def bmkg_fetch_autogempa() -> dict:
    resp = _get_with_retry(BMKG_AUTOGEMPA_URL)
    return resp.json()


def save_json(obj: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
