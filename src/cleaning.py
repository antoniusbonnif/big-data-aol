"""Operasi pembersihan & organisasi data gempa: USGS (raw JSON per tahun) + BMKG."""
import glob
import json
import os
import re

import numpy as np
import pandas as pd

BBOX = dict(minlat=-11, maxlat=6, minlon=95, maxlon=141)


# ---------- Load ----------

def load_usgs(raw_dir: str) -> pd.DataFrame:
    """Gabung semua data/raw/usgs_*.json jadi satu DataFrame flat."""
    rows = []
    for path in sorted(glob.glob(os.path.join(raw_dir, "usgs_*.json"))):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for feat in data["features"]:
            props = feat["properties"]
            lon, lat, depth = feat["geometry"]["coordinates"]
            rows.append(dict(
                event_id=feat["id"],
                source="usgs",
                time_utc=pd.to_datetime(props["time"], unit="ms", utc=True),
                mag=props["mag"],
                mag_type=props["magType"],
                depth_km=depth,
                latitude=lat,
                longitude=lon,
                place=props["place"],
                tsunami=props["tsunami"],
                sig=props["sig"],
                mmi=props["mmi"],
                cdi=props["cdi"],
                felt=props["felt"],
                gap=props["gap"],
                dmin=props["dmin"],
                rms=props["rms"],
                nst=props["nst"],
            ))
    return pd.DataFrame(rows)


def load_bmkg(raw_dir: str) -> pd.DataFrame:
    """Parse BMKG gempaterkini.json (field string) jadi DataFrame numerik."""
    path = os.path.join(raw_dir, "bmkg_terkini.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    events = data["gempaterkini"]["Infogempa"]["gempa"]
    rows = []
    for ev in events:
        lat_val = float(ev["Lintang"].split()[0]) * (-1 if "LS" in ev["Lintang"] else 1)
        lon_val = float(ev["Bujur"].split()[0]) * (-1 if "BB" in ev["Bujur"] else 1)
        depth_km = float(re.sub(r"[^\d.]", "", ev["Kedalaman"]))
        rows.append(dict(
            event_id=f"bmkg_{ev['DateTime']}",
            source="bmkg",
            time_utc=pd.to_datetime(ev["DateTime"], utc=True),
            mag=float(ev["Magnitude"]),
            mag_type=None,
            depth_km=depth_km,
            latitude=lat_val,
            longitude=lon_val,
            place=ev["Wilayah"],
            tsunami=1 if "berpotensi" in ev["Potensi"].lower() and "tidak" not in ev["Potensi"].lower() else 0,
            sig=None, mmi=None, cdi=None, felt=None,
            gap=None, dmin=None, rms=None, nst=None,
        ))
    return pd.DataFrame(rows)


# ---------- Operasi 1: Filter/Selection ----------

def filter_indonesia(df: pd.DataFrame) -> pd.DataFrame:
    """Buang event luar Indonesia: bounding box + exclude place non-Indonesia terkenal."""
    in_bbox = (
        (df["latitude"] >= BBOX["minlat"]) & (df["latitude"] <= BBOX["maxlat"]) &
        (df["longitude"] >= BBOX["minlon"]) & (df["longitude"] <= BBOX["maxlon"])
    )
    exclude_keywords = ["Philippines", "Timor Leste", "Malaysia", "Papua New Guinea", "Australia"]
    pattern = "|".join(exclude_keywords)
    not_excluded = ~df["place"].fillna("").str.contains(pattern, case=False, regex=True)
    return df[in_bbox & not_excluded].copy()


# ---------- Operasi 2: Transformation ----------

def transform_time(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["time_utc"] = pd.to_datetime(df["time_utc"], utc=True)
    df["time_wib"] = df["time_utc"] + pd.Timedelta(hours=7)
    df["year"] = df["time_utc"].dt.year
    df["month"] = df["time_utc"].dt.month
    return df


# ---------- Operasi 3: Deduplication ----------

def deduplicate(df: pd.DataFrame, time_window_sec: int = 60, coord_round: int = 2) -> pd.DataFrame:
    """Event USGS & BMKG yang sama (lokasi dekat + waktu dekat) dianggap duplikat."""
    df = df.copy()
    df["_lat_r"] = df["latitude"].round(coord_round)
    df["_lon_r"] = df["longitude"].round(coord_round)
    df["_time_bucket"] = (df["time_utc"].astype("int64") // 10**9 // time_window_sec)
    df = df.sort_values("source")  # prioritas usgs (alfabet lebih dulu dari bmkg terbalik, cek eksplisit)
    df = df.drop_duplicates(subset=["_lat_r", "_lon_r", "_time_bucket"], keep="first")
    return df.drop(columns=["_lat_r", "_lon_r", "_time_bucket"])


# ---------- Operasi 4: Join (validasi silang, bukan merge kolom) ----------

def cross_validate_join(df: pd.DataFrame) -> pd.DataFrame:
    """Tandai event yang muncul di lebih dari satu sumber dalam window waktu+lokasi sama (cross-check)."""
    df = df.copy()
    df["_lat_r"] = df["latitude"].round(1)
    df["_lon_r"] = df["longitude"].round(1)
    df["_time_bucket"] = (df["time_utc"].astype("int64") // 10**9 // 300)  # 5 menit
    counts = df.groupby(["_lat_r", "_lon_r", "_time_bucket"])["source"].transform("nunique")
    df["cross_validated"] = counts > 1
    return df.drop(columns=["_lat_r", "_lon_r", "_time_bucket"])


# ---------- Operasi 5: Imputation ----------

def impute_missing(df: pd.DataFrame) -> pd.DataFrame:
    """mmi/cdi/felt banyak null (hanya diisi untuk gempa dirasakan) -> flag 'tidak dilaporkan', bukan drop."""
    df = df.copy()
    for col in ["mmi", "cdi", "felt"]:
        df[f"{col}_missing"] = df[col].isna().astype(int)
        df[col] = df[col].fillna(-1)
    for col in ["gap", "dmin", "rms", "nst"]:
        df[col] = df[col].fillna(df[col].median())
    df["mag_type"] = df["mag_type"].fillna("unknown")
    return df


# ---------- Operasi 6: Binning ----------

def add_bins(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["depth_class"] = pd.cut(
        df["depth_km"], bins=[-1, 70, 300, np.inf],
        labels=["shallow", "intermediate", "deep"],
    )
    df["mag_band"] = pd.cut(
        df["mag"], bins=[0, 4.5, 5.5, 6.5, 10],
        labels=["4.0-4.5", "4.5-5.5", "5.5-6.5", "6.5+"],
    )
    df["zone_lat"] = (df["latitude"] // 1).astype(int)
    df["zone_lon"] = (df["longitude"] // 1).astype(int)
    df["zone_id"] = df["zone_lat"].astype(str) + "_" + df["zone_lon"].astype(str)
    return df


# ---------- Operasi 7: Aggregation ----------

def aggregate_zone_month(df: pd.DataFrame) -> pd.DataFrame:
    """Agregasi jumlah event & rata-rata magnitude per zona per bulan (dipakai untuk EDA/fitur)."""
    agg = (
        df.groupby(["zone_id", "year", "month"])
        .agg(event_count=("event_id", "count"), avg_mag=("mag", "mean"), max_mag=("mag", "max"))
        .reset_index()
    )
    return agg
