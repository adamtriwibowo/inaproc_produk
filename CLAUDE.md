# CLAUDE.md – INAPROC Bulk Upload Assistant

Proyek ini adalah website internal multi-perusahaan untuk menyiapkan upload massal produk ke INAPROC Katalog Elektronik v6.

- **Spesifikasi lengkap:** `PROMPT_CLAUDE_CODE.md`
- **Sumber kebenaran aturan INAPROC:** `knowledge/PENGETAHUAN_INAPROC.md`. Baca sebelum mengubah logika template, validasi, atau KBLI.
- **Dataset (jangan scraping ulang):** `data/` berisi kategori 58›451›2.870, KBLI per kategori, nama KBLI, KBLI pt.kig, status Bisa/Tidak Bisa, dan produk existing.
- **Template resmi:** `templates/`, dengan skema di `templates/tpl_info.json`. Jangan pernah mengubah baris 1–6, sheet pendukung, atau data validation saat menulis template. Gunakan openpyxl.
- **Golden reference** (file yang sudah diterima INAPROC): `data/contoh_berhasil_diunggah/`. Semua perubahan generator wajib lolos golden test.
- **Script referensi yang sudah terbukti:** `scripts/convert.py` (Form → template → zip).

Aturan kritis:
1. Kategori bisa diisi ⇔ ada KBLI perusahaan (kode **dan** versi) di `kbliCodes` kategori.
2. Data template ditulis mulai baris 7 setelah `delete_rows(7,3)`. Kolom U selalu kosong. Kolom berlabel (Kosongkan) dibiarkan kosong untuk Jasa.
3. Foto berupa link publik **.png**. Nama produk 10–100 karakter. Harga nett berupa angka bulat.
4. Produk hasil unggah **langsung tayang**; status "Tidak Tayang" diabaikan INAPROC. Unggahan tidak bisa dibatalkan, jadi ekspor zip hanya untuk batch yang sudah disetujui Reviewer.
5. Multi-perusahaan: semua data di-scope per `company_id`, dan Institution ID template harus cocok dengan perusahaan aktif.
6. Jangan menyimpan kredensial INAPROC dan jangan scraping dari server. UI berbahasa Indonesia.
