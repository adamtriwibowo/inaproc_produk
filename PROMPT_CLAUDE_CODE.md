# Prompt untuk Claude Code — Website "INAPROC Bulk Upload Assistant"

> Folder kerja: `D:\Adam Website\inaproc_upload_produk`. Buka Claude Code di folder itu, lalu salin seluruh isi di bawah garis.
> Kit (`knowledge/`, `data/`, `scripts/`, `templates/`) sudah ada di folder ini, dan `CLAUDE.md` otomatis dibaca Claude Code.

---

Kamu akan membangun aplikasi web internal **multi-perusahaan** **INAPROC Bulk Upload Assistant** untuk satu atau lebih penyedia Katalog Elektronik INAPROC v6 (penyedia.inaproc.id). Tujuannya: memudahkan tim menyiapkan produk dalam jumlah banyak lalu menghasilkan file **.zip** yang siap diunggah lewat menu *Atur Produk Sekaligus → Unggah Dokumen*. Aplikasi ini **tidak** login ke INAPROC dan **tidak** mengunggah otomatis. Unggahan tetap dilakukan manusia.

## 0. Baca dulu sebelum menulis kode
1. `knowledge/PENGETAHUAN_INAPROC.md` adalah sumber kebenaran semua aturan: KBLI, struktur template, kolom wajib, dropdown, foto, dan pelajaran dari uji unggah.
2. `templates/*.xlsx` berisi 15 template resmi (14 Spare Part Mobil Barang dan 1 Jasa Servis Mobil). `templates/tpl_info.json` adalah hasil scan kolom, data validation, dan KBKI per template.
3. `scripts/convert.py` adalah konverter Form → template → zip yang **sudah terbukti berhasil diunggah**. Porting logikanya, jangan ditulis ulang dari nol. `scripts/tplscan.py` membaca skema template. `scripts/form.py` membuat form input. `scripts/browser_snippets.js` adalah snippet DevTools untuk cek KBLI.
4. `data/contoh_berhasil_diunggah/` berisi file **golden reference** (3 template terisi dan form dummy) yang diterima INAPROC. Output generator harus identik secara struktur dengan file ini.
5. `data/kategori_produk_status_kbli.csv`, `subkategori_status.csv`, `kategori_utama_status.csv`, `kbli_perusahaan.json`, dan `inaproc_kategori_kbli.json` adalah snapshot kelayakan 2.870 kategori terhadap KBLI perusahaan.

**Dataset sudah tersedia di folder ini, jadi jangan scraping ulang.** Saat aplikasi pertama kali dijalankan, buat *seed*:
- perusahaan pertama Katalog Indonesia Group (pt.kig) dari `data/kbli_perusahaan.json`
- pohon 58 › 451 › 2.870 kategori dan kode KBLI per kategori dari `data/inaproc_kategori_kbli.json` (lihat `scripts/build.py` untuk cara membacanya: `l1`, `l2`, `cd`, `rows`)
- nama KBLI dari `data/inaproc_nama_kbli.json`
- status per kategori dari `data/kategori_produk_status_kbli.csv` (bisa dipakai sebagai cross-check hasil hitung)
- produk existing dari `data/produk_existing_pt_kig.json`
- skema 15 template dari `templates/`

Catatan: `inaproc_kategori_kbli.json` belum menyimpan ID kategori (UUID). ID kategori didapat dari sel B2 template atau dari impor `inaproc_kbli_check.json` (hasil `browser_snippets.js`, yang sudah menyertakan `id`). Rancang model data supaya UUID bisa diisi belakangan dan pencocokan sementara memakai path nama L1›L2›L3.

Ringkas rencanamu (arsitektur, model data, halaman) dan tunggu persetujuanku sebelum membangun.

## 1. Stack yang disarankan
- **Backend: Python FastAPI, openpyxl, Pillow, SQLite (SQLModel).** openpyxl wajib dipakai untuk menulis template supaya baris 1–6, sheet pendukung, dan data validation tetap utuh. Jangan pakai SheetJS untuk menulis template.
- **Frontend: React (Vite atau Next.js), Tailwind, dan tabel grid yang bisa diedit** (misalnya AG Grid Community atau TanStack Table) dengan dukungan paste dari Excel.
- Auth sederhana (email + password, hash bcrypt) dengan role. Jalankan dengan `docker compose up`.
- Test: pytest untuk backend, termasuk golden test.

## 2. Multi-perusahaan, role, dan alur kerja

### 2a. Pilih perusahaan dulu (multi-tenant)
Saya mengelola **beberapa perusahaan penyedia**, masing-masing dengan akun INAPROC, Institution ID, dan **KBLI yang berbeda**. Karena itu:
- Setelah login, pengguna **wajib memilih perusahaan** dari daftar perusahaan yang boleh ia akses. Kalau hanya punya akses ke satu perusahaan, perusahaan itu langsung terpilih. Nama perusahaan aktif selalu tampil di header, dengan **pengalih perusahaan** (company switcher).
- **Semua data terikat ke perusahaan (`company_id`)**: KBLI, hasil cek kelayakan kategori, template, batch, produk, foto, rekomendasi, dan riwayat unggah. Tidak boleh ada data perusahaan A yang terlihat atau terpakai di perusahaan B. Terapkan di setiap query/endpoint backend (bukan hanya disembunyikan di UI), dan tambahkan test-nya.
- Entitas **Perusahaan**: nama, nama toko INAPROC, akun/email INAPROC (sebagai teks saja, **tanpa password**), `institution_id` INAPROC, skala usaha, logo opsional, dan daftar KBLI (kode, versi, nama).
- **Kelayakan kategori dihitung per perusahaan**: kategori yang sama bisa "Bisa" di perusahaan A tapi "Tidak Bisa" di B. Pohon kategori dan master KBLI bersifat global (cache bersama), sedangkan statusnya per perusahaan.
- **Template terikat ke perusahaan**: sel B1 (`Institution ID`) di template harus sama dengan `institution_id` perusahaan aktif. Kalau berbeda, **tolak** dengan pesan jelas ("Template ini milik perusahaan lain"). Saat ekspor, cek lagi bahwa semua file di zip ber-Institution ID perusahaan aktif.
- Impor `inaproc_kbli_check.json` (dari `browser_snippets.js`) juga divalidasi: `institutionId` di file harus sama dengan perusahaan aktif. Petunjuk di UI: "Jalankan snippet saat login ke akun INAPROC perusahaan ini."
- Data snapshot di `data/` adalah milik perusahaan pertama: **Katalog Indonesia Group (pt.kig)**, Institution ID `01J8T3EVSG6715EVP9CF9ZQV4V`. Jadikan seed perusahaan pertama.
- Dashboard per perusahaan: jumlah kategori Bisa/Tidak Bisa, batch per status, dan produk yang sudah diunggah. Super Admin juga punya ringkasan lintas perusahaan.

### 2b. Role berdasarkan akses ke perusahaan
Role disimpan sebagai **keanggotaan (user × perusahaan × role)**. Satu orang bisa menjadi Operator di perusahaan A sekaligus Reviewer di perusahaan B, dan tidak punya akses sama sekali ke perusahaan C.

| Role | Cakupan | Hak |
|---|---|---|
| **Super Admin** | Global | Membuat/menonaktifkan perusahaan, mengundang pengguna, memberi atau mencabut akses perusahaan dan role, melihat semua perusahaan. |
| **Admin Perusahaan** | Per perusahaan | Mengelola anggota perusahaan itu; mengimpor/menyegarkan data KBLI dan kelayakan kategori; mengunggah template INAPROC; melihat semua batch perusahaan itu. |
| **Operator Input** | Per perusahaan | Membuat batch, mengisi produk (grid/form/impor Excel), mengunggah foto, memperbaiki error validasi, mengajukan ke review. Tidak bisa membuat zip final. |
| **Reviewer** | Per perusahaan | Memeriksa batch (produk, foto, harga), lalu menyetujui atau mengembalikan dengan catatan. Hanya batch yang **disetujui** yang bisa diekspor ke .zip. Reviewer tidak boleh menyetujui batch yang ia buat sendiri. |

- Saat berganti perusahaan, menu dan tombol menyesuaikan role pengguna di perusahaan tersebut.
- Audit log per perusahaan: siapa membuat, mengubah, menyetujui, dan mengekspor apa, beserta waktunya.

Status batch (per perusahaan): `Draft → Diajukan → Perlu Perbaikan ↔ Diajukan → Disetujui → Diekspor → Sudah Diunggah` (dicentang manual setelah tim mengunggah di INAPROC, dengan catatan hasil dari tab Riwayat).

## 3. Fitur
### A. Kelayakan Kategori (KBLI)
- Data ini **per perusahaan aktif**. Impor `inaproc_kbli_check.json` (output `scripts/browser_snippets.js`, dijalankan saat login ke akun INAPROC perusahaan tersebut) atau data snapshot di `data/` (khusus pt.kig).
- Tampilan pohon **Kategori Utama › Subkategori › Kategori Produk** dengan warna **hijau = Bisa, kuning = Sebagian, merah = Tidak Bisa**, jumlah per level, filter, dan pencarian.
- Detail kategori: KBLI 2020/2025 yang diterima beserta nama, dan KBLI perusahaan yang cocok.
- Halaman **KBLI**: KBLI perusahaan dan KBLI yang paling banyak membuka kategori "Tidak Bisa".
- Halaman **Rekomendasi**: kategori "Bisa" yang belum punya produk. Prioritas 1 = subkategori yang sudah diisi, 2 = kategori utama yang sudah diisi, 3 = kategori utama baru. Beri flag catatan (izin edar alkes, alat berat, BMKG, reseller software).
- Peringatan untuk produk existing yang kategorinya kini "Tidak Bisa".
- Ekspor rekap ke Excel.
- **Aturan:** kategori Bisa ⇔ ada `kode|versi` KBLI perusahaan di `kbliCodes` kategori.

### B. Manajemen Template
- Admin mengunggah file template `.xlsx` dari INAPROC (satu atau banyak, atau sebuah zip). Sistem membaca otomatis:
  - `Category ID` (B2), `Template ID` (B3), `Institution ID` (B1)
  - jenis (Barang/Jasa dari nama file atau baris 6), kolom baris 4–6
  - data validation per kolom, isi sheet Daftar KBKI / Satuan / Negara / PPNBM
- Simpan sebagai **skema kategori**: kolom, label, wajib/opsional/kosongkan, dan pilihan dropdown.
- Tolak template kategori yang statusnya "Tidak Bisa" menurut data KBLI.
- Peringatkan bila kategori yang dipilih Operator belum punya template, lalu arahkan untuk mengunduhnya di INAPROC (maksimal 100 kategori per unduhan, dikirim lewat email).

### C. Input Massal (inti, harus sangat mudah dipakai)
- **Satu batch boleh berisi banyak kategori.** Grid utama punya kolom *Kategori* (dropdown, hanya kategori "Bisa" yang punya template). Kolom atribut di kanan **berubah dinamis** mengikuti skema kategori baris tersebut. Contoh: Barang punya Tipe/Spesifikasi/Garansi, Jasa Servis punya Rincian Layanan/Komponen Biaya Personil.
- Grid terpisah untuk **Barang** dan **Jasa**. Untuk Jasa, kolom berat, dimensi, dan pengiriman disembunyikan.
- **Paste dari Excel**, isi ke bawah (fill-down), duplikat baris, dan **impor** file `Form_Data_Produk_*.xlsx` (format dari `scripts/form.py`). Sediakan juga unduhan form kosong yang dibuat dari skema.
- Default pintar: PPN 12%, PPnBM Tidak Aktif, Kuantitas desimal Tidak Aktif, Min. beli 1, Opsi pengiriman STANDARD (Barang), Negara IDN. Pilihan PDN di-preset dari pilihan "Lokal" atau "Impor" (preset bisa diubah per baris).
- **KBKI otomatis**: jika kategori hanya punya 1 kode, langsung terisi. Jika lebih dari 1, tebak dari nama produk (lihat `pick_kbki` di convert.py) dan tandai "perlu dicek".
- **Validasi real-time per sel**, berdasarkan aturan di PENGETAHUAN_INAPROC.md:
  - nama 10–100 karakter
  - kolom wajib per skema terisi
  - nilai dropdown persis sama dengan pilihan
  - harga, stok, dan berat berupa bilangan bulat > 0 (harga nett, tanpa pemisah)
  - Pre Order Aktif ⇒ jumlah hari wajib
  - PPnBM Aktif ⇒ kolom N–P wajib
  - foto utama wajib berupa link publik `.png` (atau file yang diunggah dan diproses)
  - kolom "(Kosongkan)" dipaksa kosong
  - kolom U (Klasifikasi PDN) selalu kosong
  - deteksi nama duplikat dalam batch maupun dengan produk existing
- Panel error per batch dengan klik langsung ke sel yang bermasalah. Batch tidak bisa diajukan selama masih ada error.
- **Tidak tersedia di upload massal** (tampilkan sebagai catatan, bukan input): varian, harga grosir, layanan tambahan, merek, TKDN, SNI. Buat daftar "tindak lanjut manual di INAPROC" per produk.

### D. Foto
- Unggah foto per produk (drag & drop, banyak sekaligus, dicocokkan ke produk lewat nama file).
- Proses otomatis: koreksi orientasi EXIF, pad ke 1:1 dengan latar putih (opsi crop), resize ke 700×700 (min 300, maks 2048), simpan **PNG < 1 MB** (turunkan resolusi atau kuantisasi bila perlu), dan tampilkan pratinjau.
- Template membutuhkan **link publik .png**. Sediakan:
  1. kolom untuk menempelkan link (imgur atau Google Drive dengan akses "siapa saja dengan link"), divalidasi formatnya;
  2. opsional (fase 2): integrasi Google Drive API untuk mengunggah dan mengatur izin publik secara otomatis.
  - Unduh semua foto hasil proses dalam satu zip.
- Generator banner sederhana untuk produk **Jasa** (nama layanan, poin layanan, nama perusahaan), 1:1, PNG.

### E. Review & Ekspor
- Reviewer melihat ringkasan batch: jumlah produk per kategori, galeri foto, harga, dan daftar peringatan (KBKI tebakan, foto belum punya link).
- Ekspor (hanya batch Disetujui):
  - untuk setiap kategori, salin template aslinya
  - `delete_rows(7, 3)`, lalu tulis data mulai baris 7 sesuai pemetaan kolom
  - kolom C = "Tayang"
  - pertahankan nama file asli
  - zip **tanpa folder**, ≤ 50 MB (bila lebih, pecah menjadi beberapa zip)
  - sertakan `laporan_batch.xlsx` sebagai file terpisah, tidak di dalam zip unggahan
- Tampilkan peringatan besar sebelum unduh zip: **"Produk akan langsung TAYANG dan bisa dibeli setelah diunggah. Unggahan tidak bisa dibatalkan."** Wajib dicentang.
- Setelah tim mengunggah, mereka mencatat hasil dari tab Riwayat INAPROC (berhasil/gagal dan pesan error). Baris yang gagal bisa dibuka kembali untuk diperbaiki.

### F. Mode Uji Coba
- Toggle "Batch uji coba": nama otomatis diberi awalan `[DUMMY]` dan muncul pengingat untuk **menghapus produk dari INAPROC segera setelah tes** (status Tidak Tayang di template diabaikan INAPROC).

## 4. Kriteria selesai
1. **Golden test**: mengimpor `data/contoh_berhasil_diunggah/Form_Data_Produk_DUMMY.xlsx`, lalu ekspor (status "Tidak Tayang" untuk test), menghasilkan 3 file yang nilai sel baris 1–7 dan sheet pendukungnya sama dengan file golden di folder yang sama.
2. Semua 15 template di `templates/` bisa diimpor sebagai skema tanpa error, dan atribut Barang vs Jasa terdeteksi benar.
3. Validasi menolak contoh kasus: nama 8 karakter, harga "85.000", Pre Order tanpa hari, foto .jpg, satuan di luar daftar, KBKI yang bukan milik kategori.
4. Pohon kelayakan menampilkan 756 Bisa / 2.114 Tidak Bisa (snapshot), dan 29 kategori utama yang punya ≥1 kategori Bisa.
5. Role diuji **per perusahaan**: Operator tidak bisa mengekspor zip, Reviewer bisa menyetujui (kecuali batch buatannya sendiri), dan Admin Perusahaan bisa mengunggah template.
5b. Multi-perusahaan diuji:
   - Pengguna dengan akses hanya ke perusahaan A mendapat 403/404 saat mengakses data B lewat API.
   - Template ber-Institution ID B ditolak di perusahaan A.
   - Kategori yang sama berstatus berbeda di A dan B sesuai KBLI masing-masing.
   - Pengguna yang Operator di A dan Reviewer di B mendapat menu yang benar setelah berganti perusahaan.
6. README berisi cara menjalankan, alur kerja tim, dan cara menyegarkan data KBLI lewat `browser_snippets.js`.

## 5. Batasan
- Jangan menyimpan kredensial atau cookie INAPROC. Jangan melakukan scraping INAPROC dari server.
- Jangan mengarang data produk. Semua data berasal dari pengguna.
- Antarmuka berbahasa Indonesia.
