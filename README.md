# big-data-aol

Assignment II — COMP8035041 Big Data Analytics.
Prediksi risiko gempa bumi Indonesia (USGS + BMKG) — ML pipeline (sklearn + Spark MLlib) + graph analytics.

## Struktur

```
data/
  raw/         data mentah hasil ingestion (immutable)
  interim/     hasil antara proses cleaning
  processed/   earthquake_features.parquet (kontrak antar notebook)
notebooks/
  01_ingestion.ipynb        ambil data USGS + BMKG
  02_cleaning.ipynb         operasi data: filter, transform, dedup, join, impute, bin, aggregate
  03_ml_sklearn.ipynb       model tanpa Spark (Logistic Regression, RF, GB)
  04_ml_spark.ipynb         model dengan Spark MLlib (jalan di Colab)
  05_graph_analytics.ipynb  graph spasial-temporal + bipartite wilayah
src/        fungsi reusable (ingestion, cleaning, feature engineering)
figures/    semua gambar untuk laporan
laporan/    Assignment_II.docx
```

## Jalan di Colab

```python
from google.colab import drive
drive.mount('/content/drive')

!git clone https://github.com/antoniusbonnif/big-data-aol.git
%cd big-data-aol
!pip install -q -r requirements.txt
```

Tiap notebook punya sel pertama `BASE_DIR` — set ke path repo (lokal atau `/content/big-data-aol` di Colab). Sel-sel berikutnya tidak berubah.

Runtime disarankan: **CPU (High-RAM)**, tanpa GPU/TPU — semua tahap CPU-bound (pandas, sklearn, Spark MLlib, networkx), GPU tidak terpakai.

## Urutan eksekusi

```
01 → 02 → 03 ─┐
        └→ 04 ─┼→ (04 baca metrics_sklearn.json untuk banding)
        └→ 05
```

Semua notebook setelah 02 baca `data/processed/earthquake_features.parquet`.
