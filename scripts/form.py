import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment

info = json.load(open(ROOT + '/templates/tpl_info.json'))
CAT_NAMES = {
    'aki-mobil': 'Aki Mobil', 'ban-kendaraan-besar': 'Ban Kendaraan Besar',
    'ban-kendaraan-industri-lainnya': 'Ban Kendaraan Industri Lainnya', 'ban-mobil': 'Ban Mobil',
    'bearing-mobil': 'Bearing Mobil', 'bumper-mobil': 'Bumper Mobil', 'busi-mobil': 'Busi Mobil',
    'kopling-transmisi-mobil': 'Kopling/Transmisi Mobil', 'lampu-mobil': 'Lampu Mobil',
    'radiator-mobil': 'Radiator Mobil', 'rem-mobil': 'Rem Mobil', 'shock-breaker-mobil': 'Shock Breaker Mobil',
    'spare-part-mobil-lainnya': 'Spare Part Mobil Lainnya', 'velg-mobil': 'Velg Mobil'}
json.dump(CAT_NAMES, open(ROOT + '/templates/cat_names.json', 'w'))

F = 'Arial'
WAJIB = PatternFill('solid', fgColor='FFF2CC')
OPS = PatternFill('solid', fgColor='EDEDED')
HDR_W = Font(name=F, bold=True, color='000000', size=10)
body = Font(name=F, size=10)
ex_font = Font(name=F, size=10, italic=True, color='808080')
thin = Side(style='thin', color='BFBFBF'); box = Border(left=thin, right=thin, top=thin, bottom=thin)

PDN_PROD = ['Diproduksi di seluruh Indonesia', 'Diproduksi sebagian di Indonesia', 'Tidak ada yang diproduksi di Indonesia']
PDN_TK = ['Dibuat oleh seluruh tenaga kerja Indonesia di dalam negeri', 'Sebagian tenaga kerja Indonesia', 'Tidak ada tenaga kerja Indonesia']
PDN_BB = ['Seluruh bahan baku dalam negeri', 'Sebagian bahan baku dalam negeri', 'Tidak ada bahan baku dalam negeri']

import openpyxl
src = openpyxl.load_workbook(ROOT + '/templates/' + info['busi-mobil']['file'])
SATUAN = [r[0].value for r in src['Satuan Produk'].iter_rows() if r[0].value]
NEGARA = [(r[0].value, r[1].value) for r in src['Daftar Negara Asal'].iter_rows(min_row=2) if r[0].value]

wb = Workbook()

# ---------- Petunjuk ----------
ws = wb.active; ws.title = 'Petunjuk'
lines = [
    ('Form Data Produk – Spare Part Mobil & Jasa Servis Mobil (INAPROC)', Font(name=F, size=14, bold=True)),
    ('', None),
    ('Cara mengisi', Font(name=F, size=11, bold=True)),
    ('1. Isi produk barang di sheet "Barang" (14 kategori spare part), dan layanan servis di sheet "Jasa Servis Mobil".', body),
    ('2. Satu baris = satu produk. Baris abu-abu bertuliskan CONTOH hanya contoh – boleh ditimpa atau dibiarkan (akan diabaikan).', body),
    ('3. Kolom berwarna KUNING wajib diisi. Kolom ABU-ABU opsional, tapi sebaiknya diisi agar produk lebih menarik.', body),
    ('4. Kolom dengan panah ▼ berisi pilihan – pilih dari daftar, jangan diketik bebas.', body),
    ('5. Harga = harga bersih (nett) per satuan, belum termasuk ongkir & pajak. Tulis angka saja, tanpa titik/koma (contoh: 85000).', body),
    ('6. Berat dalam GRAM (1 kg = 1000). Dimensi dalam cm, dibulatkan ke atas.', body),
    ('7. Foto: link publik yang berakhiran .png (Google Drive "siapa saja yang punya link" atau imgur). Minimal 1 foto per produk.', body),
    ('   Jika belum punya link, tulis nama file fotonya saja (contoh: busi-ngk-01.jpg) lalu kirim fotonya – saya siapkan versi PNG 1:1 di bawah 1 MB.', body),
    ('8. Kolom KBKI boleh dikosongkan – akan saya pilihkan sesuai kategori & jenis barang.', body),
    ('9. Merek, varian, harga grosir, TKDN & SNI TIDAK bisa lewat upload massal – ditambahkan lewat form setelah produk masuk.', body),
    ('', None),
    ('Setelah selesai', Font(name=F, size=11, bold=True)),
    ('Kirim file ini kembali. Saya akan memindahkan data ke 15 template resmi INAPROC, mengecek semua kolom wajib & pilihan, lalu membuat file .zip siap unggah.', body),
    ('', None),
    ('Saran: untuk tes pertama cukup 2–3 produk dulu (misal 1–2 spare part + 1 jasa servis).', Font(name=F, size=10, bold=True, color='C00000')),
]
for i, (t, f) in enumerate(lines, 1):
    c = ws.cell(i, 1, t)
    if f: c.font = f
ws.column_dimensions['A'].width = 150

# ---------- Daftar Pilihan ----------
wl = wb.create_sheet('Daftar Pilihan')
lists = {
    'Kategori': [CAT_NAMES[k] for k in sorted(CAT_NAMES, key=lambda k: CAT_NAMES[k])],
    'PPN': ['12%', '0%'],
    'Satuan': SATUAN,
    'PDN_Produksi': PDN_PROD, 'PDN_TenagaKerja': PDN_TK, 'PDN_BahanBaku': PDN_BB,
    'YaTidak': ['Tidak', 'Ya'],
    'Negara': [f'{c} - {n}' for c, n in NEGARA],
}
kbki_all = []
for slug, v in info.items():
    if slug == 'jasa-servis-mobil': continue
    for code, desc in v['kbki']:
        kbki_all.append(f'{code} - {desc} [{CAT_NAMES[slug]}]')
lists['KBKI'] = sorted(set(kbki_all), key=lambda s: s.split('[')[1])
refs = {}
for j, (name, vals) in enumerate(lists.items(), 1):
    wl.cell(1, j, name).font = Font(name=F, bold=True)
    for i, v in enumerate(vals, 2):
        wl.cell(i, j, v).font = body
    col = get_column_letter(j)
    refs[name] = f"'Daftar Pilihan'!${col}$2:${col}${len(vals)+1}"
    wl.column_dimensions[col].width = 40
wl.sheet_state = 'visible'

def build(ws, cols, example, nrows=200):
    for j, (name, wajib, width, lst, note) in enumerate(cols, 1):
        c = ws.cell(1, j, name + (' *' if wajib else ''))
        c.font = HDR_W; c.fill = WAJIB if wajib else OPS; c.border = box
        c.alignment = Alignment(wrap_text=True, vertical='center', horizontal='center')
        if note: c.comment = Comment(note, 'Claude')
        ws.column_dimensions[get_column_letter(j)].width = width
        L = get_column_letter(j)
        if lst:
            dv = DataValidation(type='list', formula1=refs[lst], allow_blank=True, showDropDown=False)
            dv.error = 'Pilih dari daftar'; dv.errorTitle = 'Pilihan tidak valid'
            ws.add_data_validation(dv); dv.add(f'{L}2:{L}{nrows+1}')
    ws.row_dimensions[1].height = 45
    for j, v in enumerate(example, 1):
        c = ws.cell(2, j, v); c.font = ex_font; c.fill = PatternFill('solid', fgColor='F2F2F2')
    for r in range(3, nrows + 2):
        for j in range(1, len(cols) + 1):
            ws.cell(r, j).font = body; ws.cell(r, j).border = box
    ws.freeze_panes = 'C2'

# ---------- Barang ----------
wsb = wb.create_sheet('Barang', 1)
cols_b = [
    ('No', False, 6, None, None),
    ('Kategori', True, 26, 'Kategori', 'Pilih salah satu dari 14 kategori spare part'),
    ('Nama Produk', True, 40, None, '10–100 karakter. Sertakan merek/tipe di nama, mis. "Busi NGK Iridium IX BKR6EIX"'),
    ('Tipe / Model', False, 18, None, None),
    ('Spesifikasi Produk', False, 40, None, 'Ukuran, kompatibilitas kendaraan, material, dll.'),
    ('Deskripsi Produk', False, 45, None, None),
    ('Garansi', False, 16, None, 'mis. "6 bulan" atau "Tidak ada"'),
    ('Harga Satuan (Rp, nett)', True, 16, None, 'Angka saja tanpa titik/koma; belum termasuk ongkir & pajak'),
    ('PPN', True, 8, 'PPN', None),
    ('Jumlah Stok', True, 10, None, None),
    ('Satuan', True, 11, 'Satuan', 'mis. PCS, SET, PASANG, UNIT'),
    ('Minimum Pembelian', True, 11, None, None),
    ('Berat (gram)', True, 11, None, '1 kg = 1000 gram'),
    ('Panjang (cm)', False, 9, None, None),
    ('Lebar (cm)', False, 9, None, None),
    ('Tinggi (cm)', False, 9, None, None),
    ('Lokasi Produksi', True, 30, 'PDN_Produksi', 'Detail PDN'),
    ('Tenaga Kerja', True, 34, 'PDN_TenagaKerja', 'Detail PDN'),
    ('Bahan Baku', True, 30, 'PDN_BahanBaku', 'Detail PDN'),
    ('Negara Asal', True, 22, 'Negara', 'Untuk produk lokal pilih IDN - Indonesia'),
    ('Pre Order?', False, 9, 'YaTidak', 'Ya jika barang inden'),
    ('Lama Pre Order (hari)', False, 10, None, 'Wajib jika Pre Order = Ya'),
    ('Foto Utama (link .png / nama file)', True, 34, None, 'Link publik berakhiran .png, atau nama file foto yang akan dikirim'),
    ('Foto 2', False, 20, None, None), ('Foto 3', False, 20, None, None),
    ('Foto 4', False, 20, None, None), ('Foto 5', False, 20, None, None),
    ('URL Video (YouTube)', False, 22, None, None),
    ('Kode KBKI', False, 40, 'KBKI', 'Boleh kosong – akan dipilihkan. Pilih yang sesuai kategori [di dalam kurung]'),
    ('Catatan untuk saya', False, 30, None, None),
]
ex_b = ['CONTOH', 'Busi Mobil', 'Busi Iridium Mobil Bensin (CONTOH)', 'IX-6', 'Ulir 14mm, untuk mobil bensin 1.300–1.500cc',
        'Busi iridium untuk pembakaran lebih sempurna.', '6 bulan', 85000, '12%', 50, 'PCS', 1, 60, 3, 3, 10,
        PDN_PROD[2], PDN_TK[2], PDN_BB[2], 'JPN - Japan', 'Tidak', None, 'busi-iridium-01.jpg', None, None, None, None, None,
        None, 'Baris contoh – abaikan']
build(wsb, cols_b, ex_b)

# ---------- Jasa ----------
wsj = wb.create_sheet('Jasa Servis Mobil', 2)
cols_j = [
    ('No', False, 6, None, None),
    ('Nama Layanan', True, 40, None, '10–100 karakter, mis. "Jasa Servis Berkala Mobil Bensin 10.000 km"'),
    ('Deskripsi Layanan', False, 45, None, None),
    ('Rincian Layanan Servis', False, 45, None, 'Pekerjaan apa saja yang termasuk'),
    ('Garansi Layanan', False, 16, None, None),
    ('Harga (Rp, nett)', True, 16, None, 'Angka saja tanpa titik/koma'),
    ('PPN', True, 8, 'PPN', None),
    ('Kuota / Stok', True, 10, None, 'Berapa kali layanan bisa dipesan'),
    ('Satuan', True, 12, 'Satuan', 'mis. PEKERJAAN, PAKET, UNIT, JAM'),
    ('Minimum Pembelian', True, 11, None, None),
    ('Lokasi Produksi', True, 30, 'PDN_Produksi', 'Detail PDN – untuk jasa di Indonesia biasanya "Diproduksi di seluruh Indonesia"'),
    ('Tenaga Kerja', True, 34, 'PDN_TenagaKerja', None),
    ('Bahan Baku', True, 30, 'PDN_BahanBaku', None),
    ('Negara Asal', True, 22, 'Negara', None),
    ('Ada Komponen Biaya Personil?', False, 12, 'YaTidak', None),
    ('Komponen Biaya Lainnya', False, 30, None, None),
    ('Pre Order?', False, 9, 'YaTidak', None),
    ('Lama Pre Order (hari)', False, 10, None, None),
    ('Foto Utama (link .png / nama file)', True, 34, None, 'Untuk jasa boleh banner layanan – bisa saya buatkan'),
    ('Foto 2', False, 20, None, None), ('Foto 3', False, 20, None, None),
    ('Catatan untuk saya', False, 30, None, None),
]
ex_j = ['CONTOH', 'Jasa Servis Berkala Mobil Bensin (CONTOH)', 'Servis berkala di bengkel mitra.', 'Ganti oli mesin, filter oli, cek rem, cek aki',
        '1 bulan', 450000, '12%', 100, 'PEKERJAAN', 1, PDN_PROD[0], PDN_TK[0], PDN_BB[1], 'IDN - Indonesia', 'Ya', None, 'Tidak', None,
        '(minta dibuatkan banner)', None, None, 'Baris contoh – abaikan']
build(wsj, cols_j, ex_j)

wb.move_sheet('Daftar Pilihan', offset=10)
wb.save(ROOT + '/output/Form_Data_Produk_SparePart_JasaServis.xlsx')
print('ok', len(lists['KBKI']), len(SATUAN), len(NEGARA))
