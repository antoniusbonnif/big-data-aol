# Narasi Presentasi — Assignment II
Rancangan Solusi Big Data dan ML untuk Prediksi Risiko Gempa Bumi di Indonesia

Format tiap bagian: **[Nomor Subbab]** → *(arahkan layar ke: ...)* → narasi yang dibacakan.

---

## Pembuka

*(arahkan layar ke: halaman judul)*

"Selamat [pagi/siang], perkenalkan saya Antonius Bonni Febrianto. Presentasi ini membahas rancangan solusi Big Data dan penerapan Machine Learning untuk memprediksi risiko gempa bumi di Indonesia, menggunakan data USGS dan BMKG. Presentasi terdiri dari enam bab: pendahuluan, rancangan solusi Big Data, tata kelola IT, data, Machine Learning, dan graph analytics."

---

## BAB I PENDAHULUAN

### 1.1 Latar Belakang Masalah

*(arahkan layar ke: Gambar 1 — grafik jumlah kejadian gempa per tahun)*

"Indonesia berada di pertemuan tiga lempeng tektonik — Indo-Australia, Eurasia, dan Pasifik — sehingga jadi salah satu kawasan paling aktif secara seismik di dunia. Katalog yang saya kumpulkan mencatat 19.266 kejadian gempa magnitudo 4,0 ke atas sepanjang Januari 2015 sampai Agustus 2026. Seperti terlihat di grafik ini, jumlah kejadian per tahun relatif stabil, sekitar 1.649 kejadian per tahun, atau lebih dari empat kejadian per hari. Batang 2026 lebih rendah karena datanya baru sampai Agustus, bukan karena aktivitas menurun.

Frekuensi setinggi ini menimbulkan dua persoalan. Pertama, lembaga penanggulangan bencana tidak mungkin memberi perhatian sama ke semua 19 ribu kejadian — sebagian besar gempa menengah tidak berdampak, sebagian kecil berpotensi merusak. Jadi masalah intinya bukan mendeteksi gempa, tapi menentukan wilayah mana yang secara sistematis lebih berisiko.

Kedua, sumber data kegempaan di Indonesia terpecah — BMKG cepat tapi hanya belasan kejadian terkini dan formatnya teks bebas seperti '10 km', USGS lengkap secara historis tapi global sehingga perlu disaring, BNPB cuma dasbor tanpa API. *(tunjuk Tabel 1 kalau ada waktu)* Karena itu penelitian ini menggabungkan USGS dan BMKG ke satu pipeline analitik, lalu menerapkan Machine Learning untuk klasifikasi risiko wilayah dan graph analytics untuk memetakan keterkaitan antarwilayah."

### 1.2 Market dan Business Drivers

*(arahkan layar ke: Tabel 2 — Market dan Business Drivers)*

"Kebutuhan sistem ini didorong beberapa faktor bisnis dan kebijakan sekaligus: keselamatan publik, efisiensi anggaran mitigasi, ketahanan infrastruktur, transformasi digital pemerintah, akuntabilitas publik, sampai industri asuransi.

Yang paling terukur adalah efisiensi anggaran. Dari 430 zona seismik yang teridentifikasi, model saya mengelompokkan sekitar 15,6 persen kejadian sebagai risiko tinggi. Artinya alokasi sumber daya mitigasi bisa jauh lebih terarah dibanding pendekatan merata ke semua wilayah.

Satu driver menarik lain adalah industri asuransi — penetapan premi properti di Indonesia sekarang masih pakai zonasi statis yang jarang diperbarui. Skor risiko dari sistem ini sifatnya dinamis, dihitung ulang tiap kali ada data baru masuk."

### 1.3 Pemangku Kepentingan yang Terlibat

*(arahkan layar ke: Tabel 3 — Pemangku Kepentingan)*

"Ada delapan pemangku kepentingan dengan kebutuhan data yang berbeda-beda — dari BMKG yang perlu akses penuh ke data mentah untuk kalibrasi, BNPB dan BPBD yang perlu skor risiko agregat per wilayah, sampai masyarakat umum yang cukup dapat info agregat tingkat kabupaten tanpa data individual. Perbedaan tingkat kerincian ini yang nanti jadi dasar rancangan kontrol akses berbasis peran di Bab III."

---

## BAB II RANCANGAN SOLUSI BIG DATA

*(arahkan layar ke: Gambar 2 — Arsitektur Big Data)*

"Pipeline dirancang dalam lima lapisan: sumber data, ingestion, penyimpanan, pemrosesan, dan penyajian — masing-masing bisa dikembangkan dan diskalakan mandiri. Kontrak antarlapisan diwujudkan sebagai satu file Parquet, earthquake_features.parquet, yang dihasilkan lapisan pemrosesan dan dipakai semua proses analitik berikutnya. Jadi kalau logika pembersihan data berubah, cukup diubah di satu titik saja."

### 2.1 Metode Pengumpulan Data

*(arahkan layar ke: Tabel 4 dan Gambar 3 — alur pipeline ingestion)*

"USGS diambil lewat API FDSN, BMKG lewat endpoint JSON publik. Tantangan teknis utama: USGS membatasi maksimum 20.000 rekaman per request, sementara kebutuhan saya 23.868 kejadian — jadi saya pecah permintaan per tahun, dan sistem cek dulu jumlah rekaman lewat endpoint count sebelum menarik data; kalau masih kelebihan, dipecah lagi per kuartal otomatis.

Saya juga terapkan retry dengan exponential backoff tiga kali percobaan. Kalau satu tahun gagal total, proses tidak berhenti semua — cuma dicatat di log dan lanjut ke tahun berikutnya. Hasil akhirnya: 12 tahun berhasil diambil semua, total 23.874 rekaman USGS dan 15 rekaman BMKG."

### 2.2 Teknologi Penyimpanan Data

*(arahkan layar ke: Tabel 5 — Teknologi Penyimpanan per Layer)*

"Tiap layer pakai teknologi berbeda sesuai kebutuhan: raw zone pakai object storage berbasis JSON supaya data asli tidak berubah dan bisa diproses ulang kapan saja; processed zone pakai Apache Parquet — hasilnya, 19.266 baris dan 31 kolom cuma 1,3 MB, jauh lebih kecil dari JSON mentah yang puluhan MB; interim zone pakai CSV untuk hasil agregasi yang gampang dicek manual; lalu PostgreSQL dengan ekstensi PostGIS untuk data warehouse, dan Hive Metastore untuk katalog metadata dan lineage.

Saya sengaja tidak pakai NoSQL macam MongoDB di processed zone, karena setelah dibersihkan struktur datanya sudah sepenuhnya tabular dengan skema tetap — jadi keunggulan skema fleksibel NoSQL tidak dibutuhkan lagi di tahap ini."

### 2.3 Processing Framework

*(arahkan layar ke: Tabel 6 — perbandingan Hadoop, Spark, Flink)*

"Saya bandingkan tiga framework: Hadoop MapReduce, Apache Spark, Apache Flink. Spark saya pilih karena tiga alasan — beban kerja saya dominan batch dan pelatihan model iteratif yang butuh baca data berulang, jadi cocok dengan Spark yang menyimpan data di memori; Spark punya MLlib terpadu dalam satu pipeline; dan konsep Pipeline Spark mencegah kebocoran data antara tahap transformasi dan pelatihan.

Tapi saya juga jujur mengakui satu temuan penting: di skala data penelitian ini — cuma 19 ribuan baris — keunggulan Spark belum kelihatan dari sisi kecepatan. Nanti di Subbab 5.6 saya tunjukkan Spark MLlib justru jauh lebih lambat dari scikit-learn karena overhead JVM. Pemilihan Spark di sini murni pertimbangan skalabilitas jangka panjang, bukan efisiensi saat ini."

---

## BAB III TATA KELOLA IT

"Bab ini bahas empat aspek: security, compliance, data privacy, dan data quality. Walau data gempa ini data publik tanpa info pribadi, tata kelola tetap penting karena hasil analisisnya dipakai untuk keputusan alokasi sumber daya publik."

### 3.1 Security

"Keamanan diterapkan tiga lapis: transmisi pakai HTTPS/TLS supaya data tidak diubah di tengah jalan; penyimpanan dienkripsi baik di raw maupun processed zone dengan kunci terpisah; dan akses pakai role-based access control sesuai pemetaan stakeholder di Tabel 3 — admin akses penuh, analis data cuma baca processed zone, petugas daerah terbatas wilayahnya, publik cuma lewat dasbor agregat.

Saya juga mau cerita satu insiden nyata yang saya alami saat pengembangan: personal access token GitHub saya sempat tertulis langsung di kode notebook. Ini berisiko karena token ikut tersimpan di riwayat versi. Saya perbaiki dengan pindahkan token ke fasilitas Secrets, supaya kredensial tidak pernah muncul di kode sumber lagi."

### 3.2 Compliance

"Ada dua dimensi kepatuhan. Pertama, ketentuan sumber data — data USGS domain publik tapi tetap wajib atribusi, BMKG data publik dengan syarat tidak boleh diklaim sebagai sumber primer. Saya catat asal data lewat kolom source, dan kolom sig_estimated untuk menandai nilai yang diestimasi, bukan asli.

Kedua, UU PDP nomor 27 tahun 2022. Dataset saat ini tidak memuat data pribadi karena isinya cuma atribut fisik kejadian geologi. Tapi saya catat, kalau sistem ini nanti dikembangkan dengan data korban dan pengungsi dari BNPB, sistem otomatis masuk cakupan UU PDP — jadi kesiapan mekanisme privasi perlu dibangun dari sekarang."

### 3.3 Data Privacy

"Karena persiapan untuk pemaduan data dampak bencana ke depan, saya terapkan prinsip privacy-by-design sejak sekarang — minimisasi data, jadi atribut seperti alamat lengkap atau NIK tidak akan disimpan meski tersedia di sumber. Untuk publik, agregasi dilakukan di tingkat grid satu derajat, sekitar 111 km persegi, cukup kasar untuk tidak bisa mengidentifikasi lokasi individu."

### 3.4 Data Quality

*(arahkan layar ke: Tabel 7 — Aturan Data Quality)*

"Ada delapan aturan kualitas data yang saya terapkan — validasi rentang koordinat menyaring 4.623 rekaman di luar Indonesia; validasi wilayah administratif mengecualikan kejadian di Filipina, Timor Leste, Malaysia, Papua Nugini, Australia; deteksi duplikasi — hasilnya nihil, artinya katalog USGS sudah bersih dari sumbernya; validasi silang USGS-BMKG; standardisasi zona waktu ke UTC; dan seterusnya.

Satu keputusan yang saya mau soroti karena berlawanan dengan praktik umum: kolom mmi, cdi, felt itu 85-96 persen datanya kosong. Biasanya kolom seperti ini dibuang. Tapi saya cek lagi — ternyata kekosongan itu informatif, artinya kejadian itu tidak dirasakan atau tidak dilaporkan masyarakat. Jadi saya tidak hapus, saya tandai lewat kolom indikator terpisah, supaya model bisa membedakan 'nilai terukur' dan 'nilai tidak tersedia'."

---

## BAB IV DATA

### 4.1 Deskripsi Data

*(arahkan layar ke: Tabel 8 dan Gambar 4 — statistik & distribusi)*

"Setelah dibersihkan, dataset akhir 19.266 baris, 31 kolom, rentang 11 tahun 7 bulan, magnitudo 4,0 sampai 7,6, kedalaman 3,3 sampai 652,5 km, terbagi jadi 430 zona seismik. Ukuran filenya cuma 1,3 MB setelah kompresi Parquet.

Di Gambar 4, sebaran magnitudo menurun tajam sesuai hukum Gutenberg-Richter — makin besar magnitudo makin jarang kejadiannya. Sebaran kedalaman memusat di zona dangkal dengan ekor panjang sampai 652 km, mencerminkan zona subduksi Indonesia. Kelompok terbesar adalah gempa dangkal magnitudo 4,0-4,5, sekitar 7.906 kejadian — ini penting karena gempa dangkal biasanya guncangannya lebih kuat di permukaan dibanding gempa dalam pada magnitudo yang sama."

### 4.2 Model Data dan Operasi Data

*(arahkan layar ke: Tabel 9 — Model Data dan Operasi Data)*

"Data gempa ini multidimensi — ada dimensi temporal, spasial, atributif, dan relasional — jadi saya pakai model data hibrida. Model relasional untuk tabel utama dengan event_id sebagai primary key. Model deret waktu untuk fitur rolling window tujuh dan tiga puluh hari ke belakang, dan sembilan puluh hari ke depan untuk label. Model geospasial lewat diskretisasi grid satu derajat. Dan model graf untuk keterkaitan antarzona, yang dibahas penuh di Bab VI.

Tabel 9 ini memetakan empat belas operasi data — selection, projection, transformation, deduplication, join, imputation, discretization, aggregation, rolling window, ranking, sampai graph construction — dan tujuan masing-masing dalam konteks penelitian."

### 4.3 Dataset untuk Diolah Menggunakan Machine Learning

*(arahkan layar ke: Tabel 11 — Skema Dataset ML)*

"Dataset katalog gempa terpadu ini saya pilih untuk ML karena tiga alasan: volumenya cukup — 19.266 rekaman; atributnya lengkap secara kuantitatif untuk rekayasa fitur; dan punya dimensi temporal yang memungkinkan split data berbasis waktu serta pembentukan label prediktif dari jendela ke depan. Skemanya di Tabel 11 mencakup identitas kejadian, magnitudo, kedalaman, koordinat, indikator tsunami, skor signifikansi, metrik kualitas jaringan seismograf, dan hasil diskretisasi."

---

## BAB V MACHINE LEARNING UNTUK BIG DATA

*(bagian paling penting — porsi presentasi terbesar di sini)*

### Perumusan Masalah

"Ini saya rumuskan sebagai klasifikasi multikelas: memprediksi tingkat risiko suatu zona pada horizon 90 hari ke depan, dengan tiga kelas — rendah, sedang, tinggi. Saya tegaskan ini beda dari memprediksi magnitudo gempa itu sendiri — itu masalah yang sampai sekarang belum terpecahkan di seismologi dan tidak realistis diklaim bisa diselesaikan ML dari data katalog saja. Yang bisa diprediksi secara valid adalah tingkat aktivitas dan keparahan zona ke depan, berdasarkan pola yang sudah teramati."

### 5.1 Data Preprocessing

"Tiga hal penting di preprocessing: pertama, kolom gap, dmin, rms, nst awalnya bertipe object bukan numerik — gara-gara gabungan USGS dan BMKG yang kosong di kolom ini — dan ini bikin gagal di Spark MLlib walau scikit-learn masih toleran. Kedua, kolom sig untuk data BMKG saya estimasi proporsional terhadap kuadrat magnitudo karena BMKG tidak punya atribut setara, dan saya tandai lewat sig_estimated. Ketiga, standardisasi fitur dilakukan di dalam pipeline supaya parameter cuma dihitung dari data latih, tidak bocor dari data uji."

### 5.2 Feature Engineering

*(bagian paling penting di seluruh presentasi — arahkan layar ke: Tabel 12 — Tiga Rancangan Label)*

"Ini bagian paling krusial dari seluruh penelitian saya, karena di sinilah saya menemukan dan memperbaiki dua kebocoran data yang serius.

**Rancangan pertama**, saya buat label dari skor sig USGS dengan ambang persentil. Semua model dapat akurasi di atas 99 persen — dan itu justru mencurigakan. Setelah saya cek korelasi, ternyata sig berkorelasi 0,95 dengan mag, salah satu fitur yang saya pakai. Jadi model itu cuma menebak ulang informasi yang sudah ada di inputnya sendiri — bukan prediksi.

**Rancangan kedua**, saya ubah label jadi proksi risiko dari statistik historis zona. Akurasi turun ke 0,72, kelihatan wajar. Tapi ternyata masih ada dua cacat: label ini tetap per zona — jadi 430 zona itu masing-masing cuma punya satu label — sehingga tugasnya berubah jadi menebak lokasi, bukan menebak risiko. Saya buktikan ini dengan model yang cuma diberi koordinat lintang-bujur — akurasinya 0,9946! Dan yang kedua, ada kebocoran temporal — statistik zona dihitung dari seluruh periode data, termasuk data yang harusnya jadi data uji.

**Rancangan ketiga**, saya balik arah jendela waktunya — label dihitung dari jendela 90 hari ke depan sejak kejadian, bukan dari masa lalu atau keseluruhan periode. Ambang kelas ditentukan cuma dari data latih. 330 kejadian di ujung rentang data yang tidak punya jendela penuh, saya keluarkan dari training maupun testing."

*(arahkan layar ke: Tabel 13 — Hasil Uji Kebocoran Label)*

"Saya juga bikin prosedur uji kebocoran permanen di notebook — bandingkan model utama dengan tiga model pembanding: baseline kelas mayoritas, model hanya-koordinat, dan model hanya-metrik-jaringan-seismograf. Hasilnya di Tabel 13: model koordinat-saja turun dari 0,9946 jadi 0,6809, model metrik-jaringan-saja bahkan turun di bawah baseline. Ini bukti kuat kebocoran lewat sidik jari lokasi sudah tertutup. Menariknya, akurasi model utama nyaris sama antara rancangan kedua dan ketiga — 0,7212 vs 0,7179 — tapi maknanya beda total: yang pertama itu sebagian besar menebak lokasi, yang kedua benar-benar memprediksi aktivitas masa depan."

*(arahkan layar ke: Tabel 14 dan 15 — distribusi kelas dan daftar fitur)*

"Setelah label diperbaiki, 192 dari 430 zona punya label yang bervariasi menurut waktu; 238 sisanya tetap berlabel tunggal karena frekuensi kejadiannya terlalu rendah — median cuma lima kejadian dalam 11 tahun. Distribusi kelasnya juga timpang — rendah 59,65 persen, sedang 24,72 persen, tinggi 15,63 persen — makanya saya pakai F1 makro sebagai metrik utama, bukan akurasi.

Fitur finalnya 13 — mag, depth_km, gap, dmin, rms, nst, energy, shallow_flag, event_count_7d, event_count_30d, days_since_last_event, tsunami, mag_type. Saya sengaja keluarkan kolom sig dari fitur meski tersedia, karena sebagian komponennya baru terkumpul setelah kejadian — jadi belum tentu tersedia saat prediksi harus dilakukan secara real."

### 5.3 Algoritma Machine Learning

"Saya bandingkan tiga algoritma: Logistic Regression sebagai baseline linear; Random Forest sebagai wakil ensemble bagging, tahan pencilan dan tersedia juga di Spark MLlib sehingga bisa dibandingkan langsung; dan Gradient Boosting sebagai wakil ensemble boosting, membangun pohon berurutan memperbaiki kesalahan sebelumnya."

### 5.4 Proses Pengembangan Model dengan dan tanpa Spark MLlib

"Split data saya lakukan berdasarkan waktu, bukan acak — 2015-2022 untuk training (13.377 baris), 2023-2026 untuk testing (5.559 baris). Ini penting karena split acak pada data deret waktu akan bocor — model bisa belajar dari 2025 untuk memprediksi 2016, padahal di dunia nyata itu mustahil.

Di scikit-learn saya pakai Pipeline dengan ColumnTransformer untuk standardisasi dan one-hot encoding. Di Spark MLlib, saya jalankan di Google Colab, pipeline tujuh tahap, dan saya pastikan perhitungan label serta fitur pakai fungsi yang sama persis dengan scikit-learn supaya perbandingannya adil. Saya juga catat satu detail teknis — StringIndexer Spark mengurutkan kelas berdasarkan frekuensi, bukan abjad, jadi saya dokumentasikan pemetaan indeksnya supaya confusion matrix tidak salah dibaca."

### 5.5 Evaluasi Model

*(arahkan layar ke: Tabel 16 dan Gambar 5 — hasil evaluasi & confusion matrix)*

"Saya pakai lima metrik: akurasi, presisi makro, recall makro, F1 makro sebagai metrik utama, dan AUC one-vs-rest.

Ada satu catatan penting yang saya mau soroti karena ini pembelajaran berharga: scikit-learn dan Spark MLlib pakai skema averaging yang beda secara default — Spark defaultnya weighted, saya awalnya pakai macro di scikit-learn. Saya sempat salah membandingkan langsung dan menyimpulkan Spark lebih unggul — padahal itu keliru. Ketahuan dari satu kejanggalan aritmetika: recall Spark persis sama dengan akurasinya, yang secara matematis memang selalu terjadi pada recall weighted, tapi hampir tidak pernah terjadi pada recall makro di data timpang. Setelah dikoreksi, saya bandingkan keduanya di skema yang sama.

Hasilnya di Tabel 16: Random Forest scikit-learn F1 makro 0,6267, jadi yang terbaik. Di confusion matrix Gambar 5, kelas sedang paling sulit dikenali di ketiga model — recall-nya cuma 0,24 sampai 0,42. Yang lebih penting: kelas tinggi presisinya bagus (0,83-0,86) tapi recall-nya rendah (0,35-0,49) — artinya kalau model bilang 'zona ini berisiko tinggi', biasanya benar, tapi lebih dari separuh zona yang sebenarnya berisiko tinggi tidak terdeteksi."

### 5.6 Analisis

*(arahkan layar ke: Gambar 6 dan Gambar 7 — feature importance & perbandingan sklearn vs Spark)*

"Random Forest mengungguli Gradient Boosting di semua metrik dan lebih cepat — ini agak di luar dugaan umum. Kemungkinan penyebabnya, konfigurasi default Gradient Boosting belum cocok untuk data segaduh data gempa; Random Forest yang merata-ratakan banyak pohon independen lebih tahan terhadap noise.

Feature importance di Gambar 6 menunjukkan event_count_7d dan event_count_30d paling dominan — sesuai pemahaman seismologi bahwa aktivitas seismik punya autokorelasi, zona yang sedang aktif cenderung tetap aktif. Metrik jaringan seismograf seperti gap dan nst kontribusinya sekarang menengah saja, jauh berkurang dibanding rancangan label lama — ini pertanda bagus, artinya model sudah tidak lagi bertumpu pada sidik jari lokasi.

Untuk perbandingan scikit-learn vs Spark di Gambar 7: setelah metrik disamakan, hasilnya praktis identik — F1 weighted 0,6999 vs 0,6987, selisih cuma 0,0012, tidak bermakna. Tapi dari sisi waktu, bedanya sangat mencolok — Spark 284,99 detik vs scikit-learn 4,65 detik, sekitar 61 kali lipat, dan bahkan setelah dihitung per konfigurasi cross-validation, Spark tetap lebih lambat. Ini karena overhead JVM, serialisasi Python-JVM, dan koordinasi tugas terdistribusi — yang di skala data kecil-menengah begini jauh melebihi manfaat paralelisasinya.

Implikasinya: Spark baru unggul kalau data sudah melebihi kapasitas memori satu mesin atau memang tersebar secara inheren. Untuk skala penelitian ini, scikit-learn hasilnya setara dengan efisiensi jauh lebih tinggi — tapi saya tetap pertahankan Spark dalam rancangan untuk skalabilitas jangka panjang.

Satu hal terakhir yang saya mau tegaskan secara terbuka: pola presisi tinggi tapi recall rendah di kelas tinggi ini serius secara operasional — dalam konteks mitigasi bencana, gagal mengenali zona yang benar-benar berisiko tinggi jauh lebih berbahaya daripada false alarm. Perbaikan ke depan bisa lewat penyesuaian threshold, class weighting, atau balancing — dengan trade-off presisi yang harus disepakati bersama stakeholder."

---

## BAB VI GRAPH ANALYTICS

"Model tabular memperlakukan tiap kejadian berdiri sendiri, padahal aktivitas seismik punya keterkaitan spasial-temporal — gempa di satu zona bisa berhubungan dengan zona lain lewat perambatan tegangan atau gempa susulan. Ini yang mau ditangkap lewat graph analytics."

### 6.1 Pengembangan Graph

*(arahkan layar ke: Gambar 8 — Graph A)*

"**Graph A** memetakan 430 zona sebagai node, dengan edge terbentuk kalau ada pasangan kejadian di dua zona berjarak kurang dari 200 km dan terpisah kurang dari 7 hari — ambang ini berdasarkan karakteristik gempa susulan. Tantangan komputasinya: pendekatan naif butuh sekitar 185 juta pemeriksaan pasangan untuk 19.266 kejadian. Saya atasi dengan sliding window terurut waktu plus perhitungan haversine langsung — dari situ dapat percepatan 2,3 kali lipat, total waktu pembentukan graph sekitar 87 detik. Hasilnya 430 node, 998 edge. Warna di gambar ini menunjukkan komunitas hasil algoritma Louvain, ukuran node sebanding derajat keterhubungan."

*(arahkan layar ke: Gambar 9 — Graph B)*

"**Graph B** itu graph bipartit — 430 node wilayah di satu sisi, 9 node kategori hazard di sisi lain (3 kelas kedalaman, 4 pita magnitudo, 2 kategori tsunami). Hasilnya 439 node, 3.451 edge. Derajat node wilayah di sini langsung menunjukkan keragaman karakteristik hazard yang dialami wilayah itu."

### 6.2 Analisis dan Insight yang Diperoleh

*(arahkan layar ke: Tabel 17 — Metrik Sentralitas)*

"Ada empat temuan utama.

**Pertama**, graph spasial-temporal ternyata terpecah jadi 79 komponen — komponen terbesar mencakup 349 dari 430 zona, sisanya zona-zona terpencil yang aktivitasnya tidak berkorelasi dengan tetangga. Implikasinya, strategi pemantauan tidak bisa diseragamkan — zona dalam komponen besar bisa dipantau via jaringan, zona terpencil butuh pemantauan mandiri.

**Kedua**, di Tabel 17, lima zona PageRank tertinggi berpusat di Laut Banda dan Sulawesi — sesuai kondisi tektonik yang rumit di sana. Menariknya, kelima zona itu keperantaraannya nol — karena mereka ada di klaster padat yang semua zonanya sudah terhubung langsung. Zona keperantaraan tertinggi justru zona -4_122 di Selat Sunda, yang berperan sebagai penghubung klaster Sumatera dan Jawa — jadi PageRank tinggi menandakan pusat aktivitas, keperantaraan tinggi menandakan jembatan strategis antarklaster.

**Ketiga**, algoritma Louvain menemukan 89 komunitas — lebih banyak dari jumlah komponen terhubung, artinya komponen besar itu masih terbagi jadi subkelompok yang bisa dipakai sebagai dasar pembagian unit pemantauan regional berbasis struktur tektonik, bukan batas administratif.

**Keempat**, dari graph bipartit, 11 dari 430 wilayah punya derajat sembilan — artinya mengalami semua kategori hazard sekaligus: dangkal-menengah-dalam, semua pita magnitudo, dan riwayat tsunami. Wilayah ini di sekitar Sulawesi, Laut Maluku, dan Papua utara — butuh strategi mitigasi paling menyeluruh.

Sebagai penutup Bab VI: graph analytics ini melengkapi klasifikasi ML di Bab V dengan tiga dimensi tambahan — kedudukan zona dalam jaringan, keanggotaan komunitas, dan keragaman hazard. Ini juga membantu menutup keterbatasan model klasifikasi untuk 238 zona berfrekuensi rendah yang labelnya tidak bervariasi — buat zona itu, metrik graph memberi informasi risiko yang tidak bisa diberikan model klasifikasi."

---

## Penutup

"Ringkasnya, penelitian ini membangun pipeline Big Data end-to-end dari USGS dan BMKG, menerapkan Machine Learning untuk klasifikasi risiko dengan pembelajaran penting soal kebocoran data, dan melengkapinya dengan graph analytics untuk memetakan keterkaitan antarwilayah. Terima kasih, saya buka untuk pertanyaan."
