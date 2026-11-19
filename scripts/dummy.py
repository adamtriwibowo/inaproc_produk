"""Isi form dengan 3 produk DUMMY + buat foto placeholder PNG 1:1."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)

from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageFont
import os

wb = load_workbook(ROOT + '/output/Form_Data_Produk_SparePart_JasaServis.xlsx')
P = ['Diproduksi di seluruh Indonesia', 'Diproduksi sebagian di Indonesia', 'Tidak ada yang diproduksi di Indonesia']
T = ['Dibuat oleh seluruh tenaga kerja Indonesia di dalam negeri', 'Sebagian tenaga kerja Indonesia', 'Tidak ada tenaga kerja Indonesia']
B = ['Seluruh bahan baku dalam negeri', 'Sebagian bahan baku dalam negeri', 'Tidak ada bahan baku dalam negeri']

barang = [
    [1, 'Busi Mobil', '[DUMMY] Busi Iridium Mobil Bensin Tes Upload', 'IR-TES-01',
     'Ulir 14 mm, reach 19 mm, untuk mobil bensin 1.300–1.500 cc', 'Produk dummy untuk uji coba unggah massal. Bukan produk nyata.',
     '6 bulan', 85000, '12%', 10, 'PCS', 1, 60, 3, 3, 10, P[2], T[2], B[2], 'JPN - Japan', 'Tidak', None,
     'dummy-busi-01.png', None, None, None, None, None, None, 'DUMMY'],
    [2, 'Rem Mobil', '[DUMMY] Kampas Rem Cakram Depan Mobil Tes Upload', 'BR-TES-02',
     'Kampas rem cakram depan, 1 set isi 4 pcs, untuk MPV 1.500 cc', 'Produk dummy untuk uji coba unggah massal. Bukan produk nyata.',
     '3 bulan', 275000, '12%', 5, 'SET', 1, 900, 15, 12, 6, P[1], T[1], B[1], 'IDN - Indonesia', 'Ya', 3,
     'dummy-rem-01.png', None, None, None, None, None, None, 'DUMMY'],
]
jasa = [
    [1, '[DUMMY] Jasa Servis Berkala Mobil Bensin Tes Upload', 'Layanan dummy untuk uji coba unggah massal. Bukan layanan nyata.',
     'Ganti oli mesin, ganti filter oli, cek rem, cek aki, cek tekanan ban', '1 bulan', 450000, '12%', 20, 'PEKERJAAN', 1,
     P[0], T[0], B[1], 'IDN - Indonesia', 'Ya', None, 'Tidak', None, 'dummy-servis-01.png', None, None, 'DUMMY'],
]
for sheet, data in (('Barang', barang), ('Jasa Servis Mobil', jasa)):
    ws = wb[sheet]
    for i, row in enumerate(data, 3):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, v)
wb.save(ROOT + '/output/Form_Data_Produk_DUMMY.xlsx')

# Foto placeholder 700x700 PNG
os.makedirs(ROOT + '/output/foto', exist_ok=True)
def font(sz):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.load_default()
for fn, title, sub, color in [('dummy-busi-01.png', 'BUSI IRIDIUM', 'Mobil Bensin', (37, 99, 235)),
                              ('dummy-rem-01.png', 'KAMPAS REM', 'Cakram Depan', (220, 38, 38)),
                              ('dummy-servis-01.png', 'SERVIS BERKALA', 'Mobil Bensin', (22, 163, 74))]:
    im = Image.new('RGB', (700, 700), 'white'); d = ImageDraw.Draw(im)
    d.rectangle([30, 30, 670, 670], outline=color, width=8)
    d.rectangle([30, 30, 670, 140], fill=color)
    d.text((350, 85), 'DUMMY – UJI COBA', font=font(40), fill='white', anchor='mm')
    d.text((350, 330), title, font=font(62), fill=color, anchor='mm')
    d.text((350, 410), sub, font=font(40), fill=(60, 60, 60), anchor='mm')
    d.text((350, 600), 'Bukan produk nyata', font=font(28), fill=(120, 120, 120), anchor='mm')
    im.save(ROOT + f'/output/foto/{fn}', optimize=True)
    print(fn, os.path.getsize(ROOT + f'/output/foto/{fn}'), im.size)
