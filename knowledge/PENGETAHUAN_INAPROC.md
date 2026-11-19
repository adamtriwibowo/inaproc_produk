# Pengetahuan: Upload Berkas Sekaligus INAPROC (Katalog Elektronik v6)

Dipelajari langsung dari penyedia.inaproc.id (akun **pt.kig / Katalog Indonesia Group**, Institution ID `01J8T3EVSG6715EVP9CF9ZQV4V`) pada 19 Nov 2026, termasuk uji unggah dummy yang **berhasil**.

## 1. Kelayakan kategori berdasarkan KBLI

### Aturan (sudah diverifikasi di form)
- Kategori produk (level 3) bisa diisi jika **minimal satu KBLI perusahaan (kode + versi) ada di daftar `kbliCodes` kategori tersebut**.
- Jika tidak cocok, form Tambah Produk menampilkan: *"Anda tidak memiliki KBLI yang sesuai dengan kategori tersebut."* dan tombol Simpan nonaktif.
- Halaman **Atur Sekaligus → Unduh Template** hanya menampilkan kategori yang lolos KBLI (terbukti: 29 kategori utama muncul = 29 kategori utama yang punya ≥1 kategori "Bisa").
- Hierarki: Kategori Utama (L1, 58) › Subkategori (L2, 451) › Kategori Produk (L3, 2.870). Kategori berlabel "(Tidak Aktif)" tidak dikembalikan API.

### API (GraphQL `https://penyedia.inaproc.id/graphql`, auth = cookie sesi login, jalankan dari tab yang sudah login)
- Sesi: `GET /api/auth/session` → `user.institutionId`, `user.sellerId`.
- Pohon kategori: `allMinifiedProductCategory(input:{})` → items{id name level productType parentId children{… children{…}}}.
- KBLI per kategori: `getProductCategory(id)` → `... on ProductCategory { kbli kbliCodes { code version } curationEnabled productType }`.
- KBLI perusahaan: `getInstitutionByID(id: institutionId)` → `company.oss.project: projectV2 { kbli { kbli name versi } }`.
- Nama KBLI: `getAllKBLI(codes:[...])` (selalu versi 2020); versi 2025: `getAllKBLI(versionedCodes:[{code, classification:"kbli2025"}])`. Parameter `classification` di root diabaikan.
- Produk milik penyedia: `listProduct(query:{pagination:{page,perPage}, filter:{}})` → otomatis difilter ke penyedia yang login.
- **Rate limit**: ±600 request cepat → HTTP 429 (`retry-after` ≈ 30 dtk, body HTML). Aman: 2 worker paralel + jeda 150 ms (≈9 req/dtk), tangani 429 dengan menunggu `retry-after`.

### Snapshot KBLI perusahaan (OSS)
| Kode | Versi | Nama |
|---|---|---|
| 46100 | 2020 | Perdagangan Besar Atas Dasar Balas Jasa (Fee) Atau Kontrak *(tidak membuka kategori apa pun)* |
| 46511 | 2020 | Perdagangan Besar Komputer dan Perlengkapan Komputer |
| 46491 | 2020 | Perdagangan Besar Peralatan Dan Perlengkapan Rumah Tangga |
| 46422 | 2020 | Perdagangan Besar Barang Percetakan Dan Penerbitan |
| 46900 | 2020 | Perdagangan Besar Berbagai Macam Barang *(tidak membuka kategori apa pun)* |
| 46499 | 2020 | Perdagangan Besar Berbagai Barang Dan Perlengkapan Rumah Tangga Lainnya Ytdl |
| 18120 | 2020 | Kegiatan Jasa Penunjang Pencetakan |
| 73100 | 2020 | Periklanan |
| 46512 | 2020 | Perdagangan Besar Piranti Lunak |
| 45201 | 2020 | Reparasi Mobil |
| 46691 | 2020 | Perdagangan Besar Alat Laboratorium, Alat Farmasi Dan Alat Kedokteran |
| 45301 | 2020 | Perdagangan Besar Suku Cadang Dan Aksesori Mobil |
| 46599 | 2020 | Perdagangan Besar Mesin, Peralatan Dan Perlengkapan Lainnya |
| 62900 | 2025 | Aktivitas Jasa Teknologi Informasi dan Komputer Lainnya |

### Snapshot hasil (19 Nov 2026)
- Kategori produk: **756 Bisa / 2.114 Tidak Bisa** dari 2.870.
- Subkategori: **113 Bisa semua, 36 Sebagian, 302 Tidak Bisa**.
- Kategori utama: **7 Bisa semua, 22 Sebagian, 29 Tidak Bisa**.
- KBLI yang paling banyak membuka kategori "Tidak Bisa": 47521 v2025 (280), 46739 v2025 (266), 46639 v2020 (261), 42930 (260), 47529 (260).
- 3 produk existing ada di kategori yang kini "Tidak Bisa": Radio Device dan Repeater (2), Alat Tulis Lainnya (1).
- Snapshot berubah jika KBLI di OSS berubah → jalankan ulang pengecekan.

#### Kategori utama
| Kategori Utama | Bisa | Tidak Bisa | Status |
|---|---|---|---|
| Alat Kesehatan | 70 | 0 | BISA SEMUA |
| Alat Laboratorium | 26 | 0 | BISA SEMUA |
| Alat Penunjang Pelayanan Kesehatan | 51 | 3 | SEBAGIAN |
| Alat Transportasi | 41 | 66 | SEBAGIAN |
| Hadiah Souvenir | 1 | 22 | SEBAGIAN |
| Jasa Bidang Kesehatan | 5 | 0 | BISA SEMUA |
| Jasa Bidang Meteorologi | 2 | 23 | SEBAGIAN |
| Jasa Layanan | 15 | 65 | SEBAGIAN |
| Jasa Tenaga Kerja | 1 | 17 | SEBAGIAN |
| Pakaian dan Aksesoris Laki-Laki | 2 | 63 | SEBAGIAN |
| Pakaian dan Aksesoris Perempuan | 1 | 70 | SEBAGIAN |
| Peralatan Bidang Geofisika | 23 | 4 | SEBAGIAN |
| Peralatan Bidang Infrastruktur MKG | 3 | 0 | BISA SEMUA |
| Peralatan Bidang Klimatologi | 10 | 0 | BISA SEMUA |
| Peralatan Bidang Meteorologi | 8 | 4 | SEBAGIAN |
| Peralatan Bidang Modifikasi Cuaca | 2 | 2 | SEBAGIAN |
| Peralatan Dapur | 60 | 3 | SEBAGIAN |
| Peralatan Elektronik | 89 | 32 | SEBAGIAN |
| Peralatan Kantor | 76 | 13 | SEBAGIAN |
| Peralatan Pendidikan | 32 | 10 | SEBAGIAN |
| Perangkat Lunak/Software | 9 | 0 | BISA SEMUA |
| Perawatan Tubuh | 12 | 44 | SEBAGIAN |
| Perikanan | 15 | 40 | SEBAGIAN |
| Perkakas | 112 | 42 | SEBAGIAN |
| Perlengkapan Alat Tulis | 19 | 50 | SEBAGIAN |
| Pesawat Angkat | 7 | 40 | SEBAGIAN |
| Pesawat Angkut | 15 | 5 | SEBAGIAN |
| Pesawat Tenaga dan Produksi | 3 | 0 | BISA SEMUA |
| Pesawat/Peralatan Konstruksi Lainnya | 46 | 60 | SEBAGIAN |
| Bidang Bina Marga 2025 | 0 | 77 | TIDAK BISA |
| Bidang Cipta Karya | 0 | 70 | TIDAK BISA |
| Bidang Perumahan dan Kawasan Permukiman | 0 | 32 | TIDAK BISA |
| Bidang Sumber Daya Air | 0 | 214 | TIDAK BISA |
| Bidang Umum | 0 | 27 | TIDAK BISA |
| Hewan dan Ternak | 0 | 28 | TIDAK BISA |
| Jasa Akomodasi | 0 | 10 | TIDAK BISA |
| Jasa Bidang Geofisika | 0 | 8 | TIDAK BISA |
| Jasa Bidang Infrastruktur MKG | 0 | 6 | TIDAK BISA |
| Jasa Bidang Klimatologi | 0 | 2 | TIDAK BISA |
| Jasa Bidang Modifikasi Cuaca | 0 | 3 | TIDAK BISA |
| Jasa Penyelenggaraan Kegiatan | 0 | 1 | TIDAK BISA |
| Jasa Sewa Alat Transportasi | 0 | 39 | TIDAK BISA |
| Jasa Sewa Peralatan Elektronik | 0 | 65 | TIDAK BISA |
| Jasa Sewa Pesawat Angkat | 0 | 47 | TIDAK BISA |
| Jasa Sewa Pesawat Angkut | 0 | 20 | TIDAK BISA |
| Jasa Sewa Pesawat Tenaga dan Produksi | 0 | 3 | TIDAK BISA |
| Jasa Sewa Pesawat/Peralatan Konstruksi Lainnya | 0 | 106 | TIDAK BISA |
| Komponen Struktur | 0 | 27 | TIDAK BISA |
| Makanan dan Minuman | 0 | 111 | TIDAK BISA |
| Material Dasar Utama | 0 | 94 | TIDAK BISA |
| Material Olahan Utama | 0 | 144 | TIDAK BISA |
| Obat, Obat Bahan Alam, Vaksin dan PKMK | 0 | 10 | TIDAK BISA |
| Pekerjaan Cetak Sawah | 0 | 25 | TIDAK BISA |
| Peralatan Olahraga | 0 | 147 | TIDAK BISA |
| Perlengkapan Spiritual Adat dan Keagamaan | 0 | 3 | TIDAK BISA |
| Sarana dan Prasarana Transportasi | 0 | 23 | TIDAK BISA |
| Sistem Manajemen Keselamatan Konstruksi (SMKK) | 0 | 10 | TIDAK BISA |
| Tanaman dan Sarana Pendukung | 0 | 84 | TIDAK BISA |

#### Subkategori yang BISA semua (per kategori utama)
- **Alat Kesehatan**: Peralatan Anestesi, Peralatan Bedah Umum dan Bedah Plastik, Peralatan Gastroenterologi-Urologi, Peralatan Gigi, Peralatan Hematologi dan Patologi, Peralatan Imunologi dan Mikrobiologi, Peralatan Kardiologi, Peralatan Kesehatan Fisik, Peralatan Kimia Klinik dan Toksikologi Klinik, Peralatan Mata, Peralatan Neurologi, Peralatan Obstetrik dan Ginekologi, Peralatan Ortopedi, Peralatan Radiologi, Peralatan Rumah Sakit Umum dan Perorangan, Peralatan Telinga, Hidung, dan Tenggorokan
- **Alat Laboratorium**: Alat dan Bahan Habis Pakai Laboratorium, Alat Gelas Laboratorium, Alat Uji Laboratorium, Alat Ukur Laboratorium, Sarana dan Penunjang Laboratorium
- **Alat Penunjang Pelayanan Kesehatan**: Alat Pembersih dan Sterilisasi Lingkungan, Alat Penunjang Kerja Laboratorium Medik, Alat Simulasi Pelatihan Pelayanan Kesehatan, Alat Ukur Penunjang Pelayanan Kesehatan, Bahan Gas Medik, Bahan Penunjang Kesehatan, Furnitur Rumah Sakit
- **Alat Transportasi**: Aksesoris Mobil, Alat Kalibrasi Peralatan Uji Kendaraan, Alat Uji Kendaraan, Spare Part Mobil
- **Jasa Bidang Kesehatan**: Jasa Kemitraan Layanan Hemodialisa
- **Jasa Layanan**: Jasa Layanan Percetakan, Jasa Penyelenggaraan Manajemen Pengelola dan Pengawasan Layanan Angkutan Transportasi, Jasa Periklanan
- **Peralatan Bidang Geofisika**: Peralatan Kemagnetan Bumi, Peralatan Lightning Detector, Peralatan Seismologi Teknik Geofisika Potensial dan Tanda Waktu, Peralatan Sistem Diseminasi, Peralatan Sistem Prekursor Gempabumi, Peralatan Sistem Tanda Waktu, Peralatan Survey Drone / Airborne, Suku Cadang Bidang Geofisika
- **Peralatan Bidang Infrastruktur MKG**: Suku Cadang Infrastruktur MKG
- **Peralatan Bidang Klimatologi**: Peralatan Cuaca/Iklim, Peralatan Kualitas Udara, Suku Cadang Bidang Klimatologi
- **Peralatan Bidang Meteorologi**: Peralatan Operasional Pengamatan Udara Atas, Suku Cadang Bidang Meteorologi
- **Peralatan Bidang Modifikasi Cuaca**: Alat Operasional Modifikasi Cuaca, Suku Cadang Bidang Modifikasi Cuaca
- **Peralatan Dapur**: Peralatan Baking Kue, Peralatan Makan dan Minum, Peralatan Masak, Perlengkapan Cuci Piring
- **Peralatan Elektronik**: Alat Pendingin Udara, Alat Penyaring Udara, Elektronik Dapur, Elektronik Lainnya, Komputer dan Aksesoris, Networking, Perangkat Presentasi, Printer dan Supplies, Professional Display, Scanner, Server dan Storage, Storage, Televisi dan Sound Audio, Uninterruptible Power Supply (UPS) dan Stabilizer
- **Peralatan Kantor**: Bahan Pembersih, Peralatan Laundry
- **Peralatan Pendidikan**: Buku Nonteks, Buku Pendidikan dan Pengatahuan Lainnya, Buku Teks Pendamping, Buku Teks Utama, Furnitur Pendidikan
- **Perangkat Lunak/Software**: Software License
- **Perawatan Tubuh**: Perawatan Telinga
- **Perikanan**: Mesin Kapal Perikanan, Peralatan dan Mesin Perikanan
- **Perkakas**: Air Pressured System, Alat Angkat dan Angkut Elektrik, Alat Ukur, Generator Set, Peralatan Keamanan dan Keselamatan Transportasi, Peralatan Perkakas, Peralatan Tenaga Surya, Perkakas Lainnya, Perlengkapan Jalan, Perlengkapan Las dan Solder, Perlengkapan Listrik, Tempat Penyimpanan Lainnya, Tempat Penyimpanan Perkakas
- **Perlengkapan Alat Tulis**: Buku Tulis, Peralatan Surat
- **Pesawat Angkat**: Dongkrak, Personal Platform
- **Pesawat Angkut**: Alat Berat, Personal Basket, Robotik dan Konveyor
- **Pesawat Tenaga dan Produksi**: Mesin Perkakas dan Produksi
- **Pesawat/Peralatan Konstruksi Lainnya**: Pekerjaan Beton (Concrete Works), Pekerjaan Konstruksi Bangunan Sipil Elektrikal, Pekerjaan Konstruksi Bangunan Sipil Pertambangan, Pekerjaan Pemasangan Pipa/Gorong Gorong Tanpa Galian (Trenchless Pipe/Culvert Installation), Pekerjaan Penegakan (Erection Works), Pekerjaan Pengangkatan (Lifting Works), Pekerjaan Pengeboran Terowongan (Tunnel Boring), Pekerjaan Pengerukan dan Reklamasi (Dredging and Reclamation Works), Pekerjaan Survei, Peralatan Penunjang (Light Equipment), Produksi Material

#### Subkategori SEBAGIAN (bisa / tidak)
- Alat Penunjang Pelayanan Kesehatan › Alat dan Prasarana Pelayanan Kesehatan: 12 bisa / 1 tidak
- Alat Penunjang Pelayanan Kesehatan › Alat Penunjang Pelayanan Rawat Inap/Jalan Pasien: 4 bisa / 2 tidak
- Alat Transportasi › Perangkat Pengisian Baterai Kendaraan Listrik: 3 bisa / 1 tidak
- Hadiah Souvenir › Souvenir Umum: 1 bisa / 10 tidak
- Jasa Bidang Meteorologi › Pemeliharaan Bidang Meteorologi: 2 bisa / 1 tidak
- Jasa Layanan › Jasa Layanan Lainnya: 1 bisa / 4 tidak
- Jasa Layanan › Jasa Layanan Pemeliharaan: 1 bisa / 6 tidak
- Jasa Layanan › Jasa Servis Alat Transportasi/Kendaraan: 2 bisa / 5 tidak
- Jasa Tenaga Kerja › Jasa Tenaga Kerja Lainnya: 1 bisa / 5 tidak
- Pakaian dan Aksesoris Laki-Laki › Tas Laki-Laki: 2 bisa / 3 tidak
- Pakaian dan Aksesoris Perempuan › Tas Perempuan: 1 bisa / 5 tidak
- Peralatan Dapur › Peralatan Dapur Lainnya: 5 bisa / 1 tidak
- Peralatan Dapur › Peralatan Pendukung Masak: 10 bisa / 2 tidak
- Peralatan Elektronik › Alat Komunikasi: 2 bisa / 9 tidak
- Peralatan Elektronik › Alat Perekam: 3 bisa / 2 tidak
- Peralatan Kantor › Furnitur Kantor: 31 bisa / 5 tidak
- Peralatan Kantor › Peralatan Kamar Mandi: 9 bisa / 1 tidak
- Peralatan Kantor › Peralatan Kamar Tidur: 2 bisa / 5 tidak
- Peralatan Kantor › Peralatan Kantor Lainnya: 1 bisa / 1 tidak
- Peralatan Kantor › Peralatan Kebersihan: 11 bisa / 1 tidak
- Peralatan Pendidikan › Alat Permainan Edukasi: 1 bisa / 5 tidak
- Peralatan Pendidikan › Peralatan Penunjang Pendidikan: 11 bisa / 5 tidak
- Perawatan Tubuh › Kesehatan Gigi dan Mulut: 3 bisa / 3 tidak
- Perawatan Tubuh › Perawatan Kaki dan Tangan: 1 bisa / 7 tidak
- Perawatan Tubuh › Perawatan Rambut: 3 bisa / 6 tidak
- Perawatan Tubuh › Perawatan Wajah: 1 bisa / 8 tidak
- Perawatan Tubuh › Produk Kewanitaan: 1 bisa / 1 tidak
- Perikanan › Kendaraan Perikanan: 1 bisa / 4 tidak
- Perkakas › Alat Angkat dan Angkut Manual: 7 bisa / 1 tidak
- Perkakas › Mesin Industri: 3 bisa / 2 tidak
- Perkakas › Peralatan Keamanan dan Keselamatan Kerja: 10 bisa / 6 tidak
- Perkakas › Perlengkapan Cat: 1 bisa / 8 tidak
- Perkakas › Perlengkapan Ledeng: 1 bisa / 16 tidak
- Perkakas › Tape dan Sealant Perekat: 2 bisa / 2 tidak
- Perlengkapan Alat Tulis › Document Organizer: 3 bisa / 7 tidak
- Perlengkapan Alat Tulis › Penempel Kertas: 1 bisa / 5 tidak

Semua subkategori lain (302) **Tidak Bisa**. Daftar lengkap per kategori produk + kode KBLI yang diterima ada di `data/kategori_produk_status_kbli.csv` / `Rekap_Kategori_INAPROC_KBLI.xlsx`.

## 2. Fitur Atur Sekaligus (upload massal)
- Menu: Produk › Daftar Produk › **Atur Produk Sekaligus** → `/products/bulk-settings`. Tab: Unduh Template · Unggah Dokumen · Riwayat. Panduan resmi: tautan "Baca Panduan Penggunaan" (Google Doc).
- **Unduh Template**: *Template Baru* (produk baru) atau *Ubah Produk Tersedia* (edit). Pilih kategori L3 (maks **100 per unduhan**; hanya kategori yang lolos KBLI tampil). Klik Unduh Template → Mulai Unduh Berkas. Proses **asinkron**: file dikirim ke **email perusahaan** (ptkatalogindonesiagroup@gmail.com) dan mungkin tidak langsung terunduh di browser. Jangan klik berulang (menghasilkan email ganda).
- Satu file per kategori L3: `Unggah_Produk_Sekaligus_-_<slug>_-_Format_Umum_-_<Barang|Jasa>_-_<dd-mm-yyyy_hh-mm>.xlsx`.
- **Unggah Dokumen**: file **.zip ≤ 50 MB** berisi file-file template terisi. **Tidak bisa dibatalkan.** Hasil dilihat di tab Riwayat.
- Uji 19 Nov 2026: zip berisi 3 template (Busi, Rem, Jasa Servis) → berhasil, produk muncul publik.

### Struktur template (sheet "Daftar Produk")
- Baris 1–3: `Institution ID`, `Category ID`, `Template ID` di kolom B → **jangan diubah/dihapus**.
- Baris 4: grup kolom; baris 5: nama kolom; baris 6: (Wajib)/(Opsional)/(Kosongkan)/(Terisi otomatis).
- Baris 7–9: petunjuk + 2 contoh → **hapus**, lalu data mulai baris 7. Kolom A (Status) & B (Pesan Error) diisi sistem.
- Sheet pendukung: Daftar Layanan Pengiriman, Daftar KBKI (khusus kategori), Daftar PPNBM, Daftar Negara Asal (kode ISO-3), Satuan Produk (83 satuan).
- Kolom 1–35 (A–AI) **sama untuk semua kategori**:

| Kol | Isi | Aturan |
|---|---|---|
| C | Status Produk | Tayang / Tidak Tayang — **"Tidak Tayang" diabaikan, produk tetap tayang** |
| D | Nama Produk | Wajib, 10–100 karakter |
| E–I | Foto 1–5 | E wajib; **link publik berakhiran .png** (imgur / Google Drive "siapa saja dengan link") |
| J | URL Video | opsional |
| K | Deskripsi | opsional |
| L | PPN | 0% / 12% |
| M | Aktifkan PPnBM | Aktif / Tidak Aktif; N–P (jenis, kode dari sheet PPNBM, status bayar) wajib jika aktif |
| Q | Kode KBKI | Wajib, dari sheet Daftar KBKI (berbeda per kategori) |
| R | PDN – produksi | Diproduksi di seluruh Indonesia / Diproduksi sebagian di Indonesia / Tidak ada yang diproduksi di Indonesia |
| S | PDN – tenaga kerja | Dibuat oleh seluruh tenaga kerja Indonesia di dalam negeri / Sebagian tenaga kerja Indonesia / Tidak ada tenaga kerja Indonesia |
| T | PDN – bahan baku | Seluruh / Sebagian / Tidak ada bahan baku dalam negeri |
| U | Klasifikasi PDN | **kosongkan** (terisi otomatis LOCAL/IMPORT) |
| V | Negara Asal | kode ISO-3, mis. IDN, JPN |
| W | Kuantitas desimal | "Tidak Aktif" |
| X/Y/Z | Stok / Satuan / Min. pembelian | wajib; satuan dari sheet Satuan Produk |
| AA/AB | Pre Order / hari | Aktif/Tidak Aktif; hari wajib jika aktif |
| AC | Harga satuan | wajib, **nett** (tanpa ongkir & pajak), angka tanpa pemisah |
| AD | Berat (gram) | wajib untuk Barang; **kosongkan** untuk Jasa |
| AE–AG | P/L/T (cm) | opsional Barang; kosongkan Jasa |
| AH | Opsi Pengiriman | STANDARD (Barang); kosongkan Jasa |
| AI | Layanan Pengiriman | opsional |

- Kolom atribut (AJ ke kanan) **berbeda per kategori**:
  - Spare part mobil (14 kategori): AJ Tipe, AK Spesifikasi Produk, AL Garansi, AM Struktur Harga (Tersedia/Tidak Tersedia), AN Informasi Lainnya, AO Label Ramah Lingkungan (Memiliki/Tidak Memiliki), AP–AQ dokumen (link Google Drive).
  - Jasa Servis Mobil: AJ Rincian Layanan Servis, AK Garansi Layanan, AL Struktur Harga, AM Komponen Biaya Personil (Ya/Tidak), AN Komponen Biaya Lainnya, AO Informasi Lainnya, AP dokumen.
  - Selalu baca baris 4–6 + data validation tiap template sebelum mengisi.
- **Tidak tercakup upload massal**: varian, harga grosir, layanan tambahan, TKDN, SNI, merek → edit via form setelah produk masuk.

### KBKI per kategori (contoh yang sudah dipelajari)
- Busi Mobil 4691001002 · Aki Mobil 4642099999 · Bumper 4912999009 · Kopling/Transmisi 4912999013 · Radiator 4912999018 · Lampu 4651006999 · Bearing & Shock Breaker 4912905999
- Rem Mobil: 4912903001 servo, …002 tromol, …003 cakram, …004 sepatu, …999 lainnya
- Velg: 4912905001 penutup pelek, 4912999004 pelek
- Ban Mobil: 3611101000, 3611102000, 3611199000, 3611302000 · Ban Kendaraan Besar: 3611301000/303000/310000/313000/399000 · Ban Industri: 3611306000–309000
- Spare Part Mobil Lainnya: 15 kode (engine mounting, piston, ring piston, aki, busi, koil, klakson, fan belt, steering gear box, roda, knalpot, kopling, filter)
- Jasa Servis Mobil: 87141

## 3. Foto produk
- Form manual: jpg/jpeg/png, optimal 700×700, min 300×300, maks 2048×2048. Upload massal: link **.png** publik.
- Standar yang dipakai: PNG 1:1, 700×700 (latar putih/padding), < 1 MB. Gunakan foto **asli** produk; gambar buatan/ilustrasi hanya untuk banner jasa atau uji coba.

## 4. Pelajaran & aturan aman
1. **Produk hasil upload langsung TAYANG & bisa dibeli publik** (harga tampil + PPN). Data harus final. Uji coba dummy wajib dihapus segera setelah tes.
2. Jangan pernah mengarang harga/spesifikasi produk nyata — data dari penyedia.
3. Unduhan, unggah, hapus, ubah status = minta izin pengguna dulu. Klik unggah idealnya dilakukan pengguna sendiri.
4. Output tool browser terbatas (±1–4 ribu karakter) → data besar dipindahkan lewat unduhan file (Blob) ke folder Downloads, lalu dibaca.
5. Saat mengisi template dengan openpyxl: hapus baris 7–9 dengan `delete_rows(7,3)`, tulis data mulai baris 7, simpan dengan nama file asli, zip tanpa folder.
