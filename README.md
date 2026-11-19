# Kit: agent_upload_berkas_sekaligus_inaproc

Isi kit ini adalah semua yang dipelajari saat mengerjakan katalog INAPROC untuk Katalog Indonesia Group (pt.kig), 19 Nov 2026.

| Folder/file | Isi |
|---|---|
| `PROMPT_CLAUDE_CODE.md` | Prompt untuk membangun website lewat Claude Code |
| `knowledge/PENGETAHUAN_INAPROC.md` | Semua aturan: KBLI, template, kolom, foto, pelajaran uji unggah |
| `data/kategori_produk_status_kbli.csv` | 2.870 kategori produk dengan status Bisa/Tidak Bisa dan KBLI |
| `data/subkategori_status.csv`, `kategori_utama_status.csv` | Rekap per level |
| `data/kbli_perusahaan.json` | 14 KBLI perusahaan (OSS) |
| `data/inaproc_kategori_kbli.json`, `inaproc_nama_kbli.json` | Data mentah (pohon kategori, kode KBLI, nama KBLI) |
| `data/Rekap_Kategori_INAPROC_KBLI.xlsx` | Rekap Excel lengkap dan rekomendasi |
| `data/Form_Data_Produk_SparePart_JasaServis.xlsx` | Form input kosong |
| `data/contoh_berhasil_diunggah/` | Golden reference: 3 template terisi yang **diterima INAPROC**, form dummy, dan foto |
| `templates/` | 15 template resmi dan `tpl_info.json` (skema hasil scan) |
| `scripts/convert.py` | Form → template → zip (sudah terbukti berhasil) |
| `scripts/form.py`, `tplscan.py`, `build.py`, `dummy.py` | Generator form, scanner template, pembuat rekap, data dummy |
| `scripts/browser_snippets.js` | Snippet DevTools untuk cek ulang kelayakan KBLI dari akun yang sedang login |

## Menjalankan script (Windows/Mac/Linux, dari folder ini)
```
pip install openpyxl pillow
python scripts/form.py                      # buat form input kosong -> output/
python scripts/dummy.py                     # contoh form terisi + foto dummy -> output/
python scripts/convert.py output/Form_Data_Produk_DUMMY.xlsx output/zip "Tayang"
python scripts/build.py                     # rekap kategori vs KBLI -> output/Rekap_Kategori_INAPROC_KBLI.xlsx
python scripts/tplscan.py                   # scan ulang templates/ -> templates/tpl_info.json
```
Semua path relatif terhadap folder kit ini. Hasil ada di `output/`.
