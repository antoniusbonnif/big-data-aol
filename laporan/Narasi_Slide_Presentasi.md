# Narasi Presentasi — Presentasi_Assignment_II.pptx

Format: **[Slide N — Judul]** → *(arahkan layar ke: ...)* → narasi.

---

## Slide 1 — Judul

*(arahkan layar ke: halaman judul)*

"Selamat [pagi/siang]. Perkenalkan, Antonius Bonni Febrianto. Presentasi ini tentang rancangan solusi Big Data dan penerapan Machine Learning untuk memprediksi risiko gempa bumi di Indonesia — memadukan katalog historis USGS dengan data mutakhir BMKG dalam satu pipeline analitik."

## Slide 2 — Latar Belakang

*(arahkan layar ke: grafik kejadian per tahun)*

"Indonesia berada di pertemuan tiga lempeng tektonik — Indo-Australia, Eurasia, Pasifik. Katalog saya mencatat 19.266 kejadian magnitudo 4,0 ke atas dari Januari 2015 sampai Agustus 2026, rata-rata sekitar 1.649 kejadian per tahun.

Frekuensi setinggi ini bikin masalah inti bukan deteksi kejadian, tapi memprioritaskan wilayah mana yang secara sistematis berisiko lebih tinggi — karena tidak mungkin semua 19 ribu kejadian dapat perhatian sama.

Masalah kedua, sumber data terpecah: BMKG real-time tapi teks bebas, USGS historis lengkap tapi numerik, BNPB cuma dasbor tanpa API. Tanpa pipeline terpadu, analisis risiko jadi reaktif, bukan prediktif — itu yang mau saya perbaiki."

## Slide 3 — Tujuan & Ruang Lingkup

*(arahkan layar ke: tiga poin 01/02/03)*

"Ada tiga tujuan. Satu, bangun Big Data pipeline yang menyatukan USGS dan BMKG lewat ingestion, cleaning, sampai penyimpanan terkontrak dalam format Parquet. Dua, terapkan Machine Learning untuk klasifikasi tingkat risiko wilayah pada horizon 90 hari ke depan, pakai fitur historis saja, tanpa kebocoran informasi masa depan. Tiga, terapkan graph analytics untuk memetakan keterkaitan spasial-temporal antarzona seismik dan pola multihazard antarwilayah."

## Slide 4 — Arsitektur Big Data

*(arahkan layar ke: gambar arsitektur)*

"Arsitekturnya empat lapisan independen. Ingestion — USGS lewat FDSN API dipecah per tahun, BMKG lewat API publik. Penyimpanan — kontraknya satu file, earthquake_features.parquet; kalau logika cleaning berubah, kode di hilir tidak perlu diubah. Pemrosesan — mencakup cleaning, feature engineering, ML dengan scikit-learn dan Spark MLlib, sampai graph analytics. Penyajian — hasilnya laporan, model, dan graph yang siap dipakai untuk mitigasi."

## Slide 5 — Tantangan Terbesar: Tiga Lapis Kebocoran Label

*(arahkan layar ke: tiga kartu v1/v2/v3 — ini bagian paling penting, kasih waktu lebih)*

"Ini bagian paling krusial dari seluruh penelitian.

**v1** — label saya bikin dari skor sig USGS. Korelasinya 0,95 dengan fitur magnitudo, jadi akurasinya semu, di atas 99 persen — model cuma menebak ulang inputnya sendiri.

**v2** — saya ganti jadi statistik zona historis. Tapi dihitung dari SELURUH periode data, jadi labelnya konstan per zona — classifier ini diam-diam berubah jadi geolocator. Buktinya, model yang cuma dikasih koordinat lat/lon saja bisa capai akurasi 0,9946.

**v3** — saya balik ke jendela 90 hari ke depan, dan threshold-nya cuma dihitung dari data train. Setelah diperbaiki, model lat/lon-saja turun ke 0,6809 — artinya jalur kebocoran sudah tertutup."

## Slide 6 — Feature Engineering & Algoritma

*(arahkan layar ke: grafik feature importance dan confusion matrices)*

"Fitur finalnya 12 — magnitudo, kedalaman, gap, dmin, rms, nst, ditambah turunan spasial-temporal — semuanya tanpa informasi masa depan. Saya bandingkan empat algoritma: Logistic Regression, Random Forest, Gradient Boosting di scikit-learn, dan Random Forest di Spark MLlib.

Split datanya temporal, bukan random — train sampai 2022, test 2023-2026, supaya tidak ada kebocoran waktu.

Dari feature importance, Random Forest dan Gradient Boosting sepakat: fitur jaringan seismograf seperti gap, dmin, rms itu kontribusinya signifikan — bukan cuma magnitudo saja."

## Slide 7 — Hasil Evaluasi Model

*(arahkan layar ke: tabel perbandingan model dan grafik sklearn vs Spark)*

"Model terbaik: Random Forest scikit-learn, F1 macro 0,6267. Dibanding Random Forest Spark, selisih F1 weighted cuma 0,0012 — tidak bermakna, mutunya setara.

Tapi soal waktu, Spark 61 kali lebih lambat — 284,99 detik lawan 4,65 detik. Overhead JVM dan serialisasi di skala 19 ribu baris ini jauh melampaui manfaat paralelisasinya. Jadi implikasinya, Spark baru worth-it kalau skalanya jauh lebih besar dari dataset ini."

## Slide 8 — Graph Analytics

*(arahkan layar ke: Graph A dan Graph B)*

"Graph A memetakan keterkaitan spasial-temporal — 430 node, 998 edge, terbagi 89 komunitas lewat algoritma Louvain. PageRank tertinggi ada di zona -7_129, Laut Banda bagian selatan.

Graph B itu graph bipartit wilayah-hazard — 439 node, 3.451 edge. Ada 11 wilayah dengan derajat multihazard sembilan — artinya kena semua kategori hazard sekaligus — lokasinya di sekitar Sulawesi, Maluku, dan Papua utara."

## Slide 9 — Insight & Implikasi Operasional

*(arahkan layar ke: angka presisi 0,86 dan recall 0,49)*

"Ini insight yang saya mau tekankan. Presisi kelas 'tinggi' itu 0,86, tapi recall-nya cuma 0,49. Artinya kalau model bilang suatu zona berisiko tinggi, 86 persen benar — tapi model ini melewatkan sekitar separuh zona yang sebenarnya berisiko tinggi.

Dari graph, zona betweenness tertinggi ada di -4_122, Selat Sunda — ini penghubung klaster Sumatra-Jawa, jadi prioritas mitigasi dari sisi konektivitas jaringan. Menariknya, node dengan PageRank tinggi tadi betweenness-nya nol, karena mereka ada di klaster padat yang sudah saling terhubung langsung.

Implikasi mitigasinya: sistem ini cocok jadi lapisan prioritisasi awal, bukan satu-satunya sumber keputusan — perlu dikombinasikan dengan pemantauan manual untuk zona borderline supaya false negative tidak lolos begitu saja."

## Slide 10 — Kesimpulan

*(arahkan layar ke: slide penutup)*

"Sebagai kesimpulan: pipeline ini menyatukan USGS dan BMKG lewat kontrak Parquet, direplikasi end-to-end di Google Colab dan divalidasi lokal sebelum tiap push. Model teruji — tiga lapis kebocoran label saya temukan dan tutup, dan Random Forest scikit-learn jadi model final dengan F1 macro 0,6267, setara mutu dengan Spark MLlib tapi 61 kali lebih cepat di skala ini. Graph analytics mengungkap struktur konektivitas di Selat Sunda dan zona multihazard di Sulawesi-Maluku-Papua utara yang tidak kelihatan dari analisis tabular saja.

Batas yang saya akui secara jujur: recall kelas risiko tinggi masih 0,49 — arah pengembangan berikutnya adalah menambah fitur atau menyesuaikan threshold supaya deteksi zona kritis lebih sensitif. Terima kasih, saya buka untuk pertanyaan."
