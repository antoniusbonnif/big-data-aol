"""Feature engineering & label risiko untuk model klasifikasi gempa."""
import numpy as np
import pandas as pd


HORIZON_DAYS = 90


def add_risk_label(df: pd.DataFrame, horizon_days: int = HORIZON_DAYS,
                   train_until_year: int = 2022) -> pd.DataFrame:
    """
    Label risk_label (rendah/sedang/tinggi) = tingkat risiko zona pada horizon
    `horizon_days` ke DEPAN, dihitung dari kejadian yang terjadi SETELAH event
    yang bersangkutan. Fitur model seluruhnya berasal dari masa lalu/saat ini,
    sehingga tugasnya adalah prediksi sungguhan, bukan karakterisasi.

    Komponen skor (bobot sama):
      - future_event_count : jumlah kejadian di zona sama dalam (t, t+horizon]
      - future_max_mag     : magnitude maksimum di zona sama pada jendela itu

    Keduanya diubah ke peringkat persentil lalu dirata-ratakan. Ambang persentil
    60/85 dihitung HANYA dari data latih (year <= train_until_year) supaya
    distribusi data uji tidak ikut menentukan batas kelas.

    Catatan desain (revisi atas rancangan sebelumnya):
    Rancangan pertama memakai `sig` sebagai dasar label. Karena `sig`
    berkorelasi 0,95 dengan `mag`, sedangkan `mag` dipakai sebagai fitur, model
    hanya menebak ulang masukannya sendiri dan mencapai akurasi semu di atas
    99%. Rancangan kedua memakai statistik zona atas seluruh periode. Cara itu
    membuat label konstan per zona, sehingga tugas klasifikasi berubah menjadi
    identifikasi lokasi: koordinat saja sudah cukup untuk mencapai akurasi
    99,46%. Selain itu, statistik dihitung dari seluruh data termasuk periode
    uji, sehingga terjadi kebocoran temporal. Rancangan ketiga inilah yang
    dipakai: label bersumber dari masa depan, fitur dari masa lalu, dan ambang
    kelas ditetapkan hanya dari data latih.

    Kejadian yang tidak memiliki jendela masa depan penuh (mendekati akhir
    rentang data) ditandai melalui kolom `has_full_horizon` dan sebaiknya
    dikeluarkan sebelum pelatihan.
    """
    df = df.copy().sort_values("time_utc").reset_index(drop=True)
    horizon = np.timedelta64(horizon_days, "D")

    future_count = np.zeros(len(df), dtype=int)
    future_max_mag = np.zeros(len(df), dtype=float)

    for _, group in df.groupby("zone_id", sort=False):
        pos = group.index.to_numpy()
        times = group["time_utc"].to_numpy()
        mags = group["mag"].to_numpy()
        for k in range(len(pos)):
            end = times[k] + horizon
            lo = k + 1
            hi = np.searchsorted(times, end, side="right")
            if hi > lo:
                future_count[pos[k]] = hi - lo
                future_max_mag[pos[k]] = mags[lo:hi].max()

    df["future_event_count"] = future_count
    df["future_max_mag"] = future_max_mag

    data_end = df["time_utc"].max()
    df["has_full_horizon"] = df["time_utc"] <= (data_end - pd.Timedelta(days=horizon_days))

    risk_score = 0.5 * df["future_event_count"].rank(pct=True) + \
                 0.5 * df["future_max_mag"].rank(pct=True)
    df["risk_score"] = risk_score

    train_mask = (df["year"] <= train_until_year) & df["has_full_horizon"]
    p60 = risk_score[train_mask].quantile(0.60)
    p85 = risk_score[train_mask].quantile(0.85)

    df["risk_label"] = np.where(risk_score >= p85, "tinggi",
                        np.where(risk_score >= p60, "sedang", "rendah"))
    df.attrs["risk_label_thresholds"] = dict(p60=float(p60), p85=float(p85),
                                             horizon_days=horizon_days)
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


# Seluruh fitur di bawah berasal dari masa lalu atau saat kejadian berlangsung,
# sedangkan label bersumber dari jendela masa depan (lihat add_risk_label).
# Karena itu `mag`, `shallow_flag`, dan `event_count_30d` kini boleh dipakai:
# ketiganya informasi yang memang tersedia pada saat prediksi dilakukan.
# `sig` tetap dikecualikan karena merupakan skor turunan USGS yang sebagian
# dihitung dari laporan masyarakat pascakejadian, sehingga belum tentu tersedia
# pada saat prediksi.
FEATURE_COLUMNS = [
    "mag", "depth_km", "gap", "dmin", "rms", "nst",
    "energy", "shallow_flag",
    "event_count_7d", "event_count_30d", "days_since_last_event",
    "tsunami",
]
CATEGORICAL_COLUMNS = ["mag_type"]
TARGET_COLUMN = "risk_label"


def temporal_split(df: pd.DataFrame, train_until_year: int = 2022,
                   require_full_horizon: bool = True):
    """
    Pisahkan data latih dan uji berdasarkan tahun, bukan secara acak, untuk
    mencegah kebocoran temporal pada data deret waktu.

    Kejadian tanpa jendela masa depan penuh dikeluarkan bila
    `require_full_horizon` bernilai True, karena labelnya dihitung dari jendela
    yang terpotong sehingga tidak sebanding dengan kejadian lain.
    """
    data = df.copy()
    if require_full_horizon and "has_full_horizon" in data.columns:
        data = data[data["has_full_horizon"]]
    train = data[data["year"] <= train_until_year].copy()
    test = data[data["year"] > train_until_year].copy()
    return train, test
