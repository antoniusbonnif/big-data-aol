"""Feature engineering & label risiko untuk model klasifikasi gempa."""
import numpy as np
import pandas as pd


def add_risk_label(df: pd.DataFrame) -> pd.DataFrame:
    """
    Label risk_label (rendah/sedang/tinggi) = proxy RISIKO ZONA saat event terjadi,
    bukan severity event itu sendiri. Dibangun dari histori zona sebelum event
    (event_count_30d, rasio event dangkal, rasio tsunami-flag zona) -- BUKAN dari
    mag/sig/depth event yang bersangkutan.

    Alasan desain: kalau label dibuat dari `sig` (yang berkorelasi 0.95 dengan
    `mag`), lalu `mag` dipakai jadi fitur, model "menebak ulang" input sendiri
    -- akurasi >99% tapi bukan model yang berguna (data leakage). Dengan proxy
    zona historis, model betul-betul memprediksi risiko dari pola wilayah,
    independen dari besaran gempa yang sedang diprediksi.

    Membutuhkan `add_ml_features` sudah dijalankan lebih dulu (perlu
    event_count_30d & zone_id). Skor risiko = weighted rank event_count_30d
    (di zona itu) + proporsi shallow_flag di zona. Threshold percentile 60/85
    dari skor training.
    """
    df = df.copy()
    zone_stats = (
        df.groupby("zone_id")
        .agg(zone_event_count=("event_id", "count"), zone_shallow_ratio=("shallow_flag", "mean"))
        .reset_index()
    )
    df = df.merge(zone_stats, on="zone_id", how="left")

    rank_count = df["zone_event_count"].rank(pct=True)
    rank_shallow = df["zone_shallow_ratio"].rank(pct=True)
    risk_score = 0.7 * rank_count + 0.3 * rank_shallow

    p60 = risk_score.quantile(0.60)
    p85 = risk_score.quantile(0.85)

    def label(score):
        if score >= p85:
            return "tinggi"
        elif score >= p60:
            return "sedang"
        return "rendah"

    df["risk_score"] = risk_score
    df["risk_label"] = risk_score.apply(label)
    df.attrs["risk_label_thresholds"] = dict(p60=p60, p85=p85)
    return df


def add_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """Fitur tambahan: energy, temporal (rolling count per zona), shallow flag."""
    df = df.copy()
    df = df.sort_values("time_utc").reset_index(drop=True)

    df["energy"] = 10 ** (1.5 * df["mag"] + 4.8)
    df["shallow_flag"] = (df["depth_km"] < 70).astype(int)

    df["event_count_7d"] = 0
    df["event_count_30d"] = 0
    df["days_since_last_event"] = np.nan

    for zone_id, group in df.groupby("zone_id"):
        idx = group.index
        times = group["time_utc"]
        for i, t in zip(idx, times):
            window7 = times[(times < t) & (times >= t - pd.Timedelta(days=7))]
            window30 = times[(times < t) & (times >= t - pd.Timedelta(days=30))]
            df.loc[i, "event_count_7d"] = len(window7)
            df.loc[i, "event_count_30d"] = len(window30)
            prior = times[times < t]
            if len(prior) > 0:
                df.loc[i, "days_since_last_event"] = (t - prior.max()).total_seconds() / 86400

    df["days_since_last_event"] = df["days_since_last_event"].fillna(9999)
    return df


# mag, sig, event_count_30d, shallow_flag SENGAJA tidak dipakai sebagai fitur --
# ketiganya komponen langsung risk_score (lihat add_risk_label), memakainya
# sebagai fitur = data leakage kedua. energy tetap dipakai (turunan mag, tapi
# beda skala/interpretasi -- fisik, bukan proxy skor) untuk representasi
# energi seismik yang relevan secara ilmiah.
FEATURE_COLUMNS = [
    "depth_km", "gap", "dmin", "rms", "nst",
    "energy", "event_count_7d", "days_since_last_event", "tsunami",
]
CATEGORICAL_COLUMNS = ["mag_type"]
TARGET_COLUMN = "risk_label"


def temporal_split(df: pd.DataFrame, train_until_year: int = 2022):
    """Split train/test berbasis tahun, bukan random -- cegah data leakage time-series."""
    train = df[df["year"] <= train_until_year].copy()
    test = df[df["year"] > train_until_year].copy()
    return train, test
