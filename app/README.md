# INAPROC Bulk Upload Assistant

Aplikasi web internal multi-perusahaan untuk menyiapkan produk massal dan menghasilkan **zip** siap unggah ke
INAPROC (Atur Produk Sekaligus → Unggah Dokumen). Aplikasi **tidak** login ke INAPROC, tidak menyimpan
kredensial INAPROC, dan tidak mengunggah otomatis. Unggahan dilakukan manusia.

Aturan sumber: `../knowledge/PENGETAHUAN_INAPROC.md`, spesifikasi: `../PROMPT_CLAUDE_CODE.md`.

## Menjalankan

### Docker
```
cd app
cp .env.example .env        # isi INAPROC_ADMIN_PASSWORD
docker compose up --build   # http://localhost:8080
```
Folder `data/` dan `templates/` dipasang read-only. Database dan foto ada di volume `storage`.

### Lokal (pengembangan)
```
# backend (Python 3.12+)
cd app/backend
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt     # Linux/Mac: .venv/bin/pip
INAPROC_ADMIN_EMAIL=admin@example.local INAPROC_ADMIN_PASSWORD=<isi> .venv/Scripts/python -m uvicorn app.main:app --port 8765
# frontend
cd app/frontend && npm install && npm run dev                              # http://localhost:5173 (proxy /api -> 8765)
```
Saat pertama dijalankan, seed otomatis: pohon 58 › 451 › 2.870 kategori, nama KBLI, perusahaan pertama
**Katalog Indonesia Group (pt.kig)** beserta KBLI, produk existing, dan 15 template. Bila
`INAPROC_ADMIN_PASSWORD` kosong, password Super Admin acak dicetak sekali di log.
Port 8000 bisa diblokir Windows, karena itu contoh memakai 8765.

### Test
```
cd app/backend && .venv/Scripts/python -m pytest tests -q
```
Mencakup golden test, enam kasus validasi, 756/2.114 kategori, 15 template, isolasi perusahaan, dan role.

## Alur kerja tim
1. **Super Admin** membuat perusahaan (nama, Institution ID, akun INAPROC sebagai teks) dan mengundang pengguna beserta role per perusahaan.
2. **Admin Perusahaan** mengisi KBLI (atau impor `inaproc_kbli_check.json`) dan mengunggah template resmi INAPROC.
3. **Operator Input** membuat batch (boleh banyak kategori), mengisi grid (tempel dari Excel, impor `Form_Data_Produk_*.xlsx`), mengunggah foto dan menempel link publik `.png`, memperbaiki error, lalu **Ajukan**.
4. **Reviewer** memeriksa ringkasan, galeri, dan peringatan, lalu **Setujui** atau **Kembalikan** dengan catatan. Reviewer tidak bisa menyetujui batch buatannya sendiri.
5. Admin/Reviewer **mengekspor zip** (wajib mencentang peringatan: produk langsung TAYANG, unggahan tidak bisa dibatalkan). `laporan_batch.xlsx` terpisah dari zip.
6. Tim mengunggah zip di INAPROC, lalu mencatat hasil di tab **Riwayat unggah** (baris gagal bisa dibuka kembali).

Status batch: `Draft → Diajukan → Perlu Perbaikan ↔ Diajukan → Disetujui → Diekspor → Sudah Diunggah`.

**Batch uji coba**: nama produk diawali `[DUMMY]`. Hapus produk dari INAPROC segera setelah tes; status "Tidak Tayang" di template diabaikan INAPROC.

## Menyegarkan data KBLI / kelayakan
1. Login ke INAPROC dengan akun **perusahaan yang bersangkutan**, buka DevTools, lalu jalankan `scripts/browser_snippets.js`.
2. Hasilnya `inaproc_kbli_check.json`. Di aplikasi: pilih perusahaan → menu **KBLI** → *Impor*.
3. `institutionId` di file harus sama dengan perusahaan aktif, kalau tidak ditolak. Impor mengganti daftar KBLI perusahaan dan mengisi UUID kategori yang masih kosong. Kelayakan dihitung ulang otomatis.
Batas rate INAPROC: sekitar 9 request/detik (lihat PENGETAHUAN_INAPROC.md).

## Keamanan & multi-perusahaan
- Semua tabel milik perusahaan memiliki `company_id`; semua endpoint di `/api/companies/{id}/...` melewati `company_ctx` (keanggotaan + role). Perusahaan yang tidak boleh diakses menghasilkan 404.
- Template ber-Institution ID perusahaan lain ditolak saat unggah dan saat ekspor.
- Password di-hash bcrypt, sesi JWT di cookie httpOnly. Gunakan `INAPROC_COOKIE_SECURE=1` di belakang HTTPS.

## Catatan fase 2
Integrasi Google Drive API (unggah foto dan atur izin publik otomatis) belum ada. Saat ini link publik ditempel manual.
