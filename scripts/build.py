import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)
import json, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

d = json.load(open(ROOT + '/data/inaproc_kategori_kbli.json'))
L1, L2, CD = d['l1'], d['l2'], d['cd']
seller = d['seller']
seller_set = {k for k, _ in seller}
JENIS = {'B': 'Barang', 'J': 'Jasa', 'DIGITAL': 'Digital'}

rows = []
for i1, i2, l3, pt, codes, ok in d['rows']:
    cs = [CD[c] for c in codes]
    c20 = sorted({c.split('/')[0] for c in cs if c.endswith('/2020')})
    c25 = sorted({c.split('/')[0] for c in cs if c.endswith('/2025')})
    match = sorted({c.replace('/', ' (') + ')' for c in cs if c.replace('/', '|') in seller_set})
    rows.append(dict(l1=L1[i1], l2=L2[i2].split('»', 1)[1], l3=l3, jenis=JENIS.get(pt, pt),
                     k20=', '.join(c20), k25=', '.join(c25), match=', '.join(match), ok=bool(ok)))
rows.sort(key=lambda r: (r['l1'].lower(), r['l2'].lower(), r['l3'].lower()))
bad = [r for r in rows if not r['ok']]

F = 'Arial'
hdr_font = Font(name=F, bold=True, color='FFFFFF')
hdr_fill = PatternFill('solid', fgColor='B91C3B')
body = Font(name=F, size=10)
bold = Font(name=F, size=10, bold=True)
title = Font(name=F, size=14, bold=True)
thin = Side(style='thin', color='D9D9D9')
box = Border(left=thin, right=thin, top=thin, bottom=thin)

def header(ws, r, cols):
    for j, c in enumerate(cols, 1):
        cell = ws.cell(r, j, c)
        cell.font, cell.fill = hdr_font, hdr_fill
        cell.alignment = Alignment(vertical='center', wrap_text=True)
        cell.border = box

def widths(ws, ws_):
    for j, w in enumerate(ws_, 1):
        ws.column_dimensions[get_column_letter(j)].width = w

wb = Workbook()

# ---------- Ringkasan ----------
ws = wb.active
ws.title = 'Ringkasan'
ws['A1'] = 'Rekap Kategori Produk INAPROC vs KBLI Perusahaan'; ws['A1'].font = title
ws['A2'] = ('Sumber: form Tambah Produk penyedia.inaproc.id (akun pt.kig), diambil 19 Nov 2026. '
            'Kategori dianggap TIDAK BISA diisi jika tidak ada satu pun KBLI perusahaan (kode + versi) '
            'yang tercantum di daftar KBLI kategori tsb; aturan ini dicek cocok dengan pesan error di form.')
ws['A2'].font = Font(name=F, size=9, italic=True); ws['A2'].alignment = Alignment(wrap_text=True, vertical='top')
ws.merge_cells('A2:E2'); ws.row_dimensions[2].height = 42

ws['A4'] = 'Total kategori (level 3)'; ws['B4'] = "=COUNTA('Semua Kategori'!D:D)-1"
ws['A5'] = 'Bisa diisi'; ws['B5'] = "=COUNTIF('Semua Kategori'!H:H,\"Bisa\")"
ws['A6'] = 'Tidak bisa diisi'; ws['B6'] = "=COUNTIF('Semua Kategori'!H:H,\"Tidak Bisa\")"
ws['A7'] = '% tidak bisa diisi'; ws['B7'] = '=IF(B4=0,0,B6/B4)'; ws['B7'].number_format = '0.0%'
for r in range(4, 8):
    ws.cell(r, 1).font = bold; ws.cell(r, 2).font = body
    ws.cell(r, 2).number_format = ws.cell(r, 2).number_format if r == 7 else '#,##0'

r0 = 9
ws.cell(r0, 1, 'Rekap per Kategori Utama').font = Font(name=F, size=12, bold=True)
header(ws, r0 + 1, ['Kategori Utama', 'Total', 'Bisa', 'Tidak Bisa', '% Tidak Bisa'])
l1s = collections.Counter(r['l1'] for r in bad)
order = sorted({r['l1'] for r in rows}, key=lambda x: (-l1s.get(x, 0), x.lower()))
r = r0 + 2
for name in order:
    ws.cell(r, 1, name)
    ws.cell(r, 2, f"=COUNTIF('Semua Kategori'!B:B,A{r})")
    ws.cell(r, 3, f"=COUNTIFS('Semua Kategori'!B:B,A{r},'Semua Kategori'!H:H,\"Bisa\")")
    ws.cell(r, 4, f"=COUNTIFS('Semua Kategori'!B:B,A{r},'Semua Kategori'!H:H,\"Tidak Bisa\")")
    ws.cell(r, 5, f'=IF(B{r}=0,0,D{r}/B{r})').number_format = '0%'
    for j in range(1, 6):
        ws.cell(r, j).font = body; ws.cell(r, j).border = box
    r += 1
first, last = r0 + 2, r - 1
ws.cell(r, 1, 'TOTAL').font = bold
for j, col in zip(range(2, 5), 'BCD'):
    ws.cell(r, j, f'=SUM({col}{first}:{col}{last})').font = bold
ws.cell(r, 5, f'=IF(B{r}=0,0,D{r}/B{r})').number_format = '0%'; ws.cell(r, 5).font = bold
for j in range(1, 6): ws.cell(r, j).border = box
ws.freeze_panes = 'A11'
widths(ws, [52, 10, 10, 12, 13])

# ---------- Tidak Bisa Diisi ----------
def detail(ws, data, cols, getters, tname):
    header(ws, 1, cols)
    for i, row in enumerate(data, 2):
        for j, g in enumerate(getters, 1):
            c = ws.cell(i, j, g(i - 1, row)); c.font = body
    ref = f'A1:{get_column_letter(len(cols))}{len(data) + 1}'
    t = Table(displayName=tname, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name='TableStyleLight9', showRowStripes=True)
    ws.add_table(t)
    ws.freeze_panes = 'A2'

ws2 = wb.create_sheet('Tidak Bisa Diisi')
detail(ws2, bad,
       ['No', 'Kategori Utama', 'Subkategori', 'Kategori Produk', 'Jenis', 'KBLI dibutuhkan (versi 2020)', 'KBLI dibutuhkan (versi 2025)'],
       [lambda n, r: n, lambda n, r: r['l1'], lambda n, r: r['l2'], lambda n, r: r['l3'], lambda n, r: r['jenis'],
        lambda n, r: r['k20'], lambda n, r: r['k25']], 'TidakBisa')
widths(ws2, [7, 38, 40, 48, 9, 40, 40])

# ---------- Semua Kategori ----------
ws3 = wb.create_sheet('Semua Kategori')
detail(ws3, rows,
       ['No', 'Kategori Utama', 'Subkategori', 'Kategori Produk', 'Jenis', 'KBLI dibutuhkan (versi 2020)', 'KBLI dibutuhkan (versi 2025)', 'Status', 'KBLI Anda yang cocok'],
       [lambda n, r: n, lambda n, r: r['l1'], lambda n, r: r['l2'], lambda n, r: r['l3'], lambda n, r: r['jenis'],
        lambda n, r: r['k20'], lambda n, r: r['k25'], lambda n, r: 'Bisa' if r['ok'] else 'Tidak Bisa', lambda n, r: r['match']],
       'Semua')
red, green = Font(name=F, size=10, color='B91C1C', bold=True), Font(name=F, size=10, color='15803D', bold=True)
for i in range(2, len(rows) + 2):
    c = ws3.cell(i, 8); c.font = green if c.value == 'Bisa' else red
widths(ws3, [7, 38, 40, 48, 9, 34, 34, 11, 30])

# ---------- KBLI Saya ----------
ws4 = wb.create_sheet('KBLI Saya')
header(ws4, 1, ['Kode KBLI', 'Versi', 'Nama KBLI', 'Jumlah kategori yang dibuka'])
for i, (k, name) in enumerate(seller, 2):
    code, ver = k.split('|')
    ws4.cell(i, 1, code); ws4.cell(i, 2, ver); ws4.cell(i, 3, name)
    n = sum(1 for r0_ in d['rows'] if any(CD[c] == f'{code}/{ver}' for c in r0_[4]))
    ws4.cell(i, 4, n)
    for j in range(1, 5): ws4.cell(i, j).font = body; ws4.cell(i, j).border = box
note_r = len(seller) + 3
ws4.cell(note_r, 1, 'Sumber: data OSS perusahaan di profil INAPROC. Kolom D = jumlah kategori yang mencantumkan KBLI tsb (satu kategori bisa dibuka beberapa KBLI).').font = Font(name=F, size=9, italic=True)
widths(ws4, [12, 8, 70, 26])

# ---------- Saran KBLI ----------
ws5 = wb.create_sheet('Saran KBLI')
cnt = collections.Counter(); l1map = collections.defaultdict(collections.Counter)
for r_ in bad:
    for c in r_['k20'].split(', '):
        if c:
            cnt[c] += 1; l1map[c][r_['l1']] += 1
header(ws5, 1, ['Kode KBLI (2020)', 'Jumlah kategori "Tidak Bisa" yang akan terbuka', 'Kategori utama terbanyak'])
for i, (c, n) in enumerate(cnt.most_common(), 2):
    ws5.cell(i, 1, c); ws5.cell(i, 2, n)
    ws5.cell(i, 3, ', '.join(f'{k} ({v})' for k, v in l1map[c].most_common(3)))
    for j in range(1, 4): ws5.cell(i, j).font = body; ws5.cell(i, j).border = box
ws5.freeze_panes = 'A2'
nr = len(cnt) + 3
ws5.cell(nr, 1, 'Dihitung dari sheet "Tidak Bisa Diisi": berapa kategori yang mensyaratkan kode KBLI 2020 tsb. Gunakan sebagai pertimbangan jika ingin menambah KBLI di OSS.').font = Font(name=F, size=9, italic=True)
widths(ws5, [18, 22, 90])

# ---------- Warna & Rekap Subkategori ----------
from openpyxl.formatting.rule import FormulaRule
G_FILL = PatternFill('solid', fgColor='C6EFCE'); G_FONT = Font(name=F, color='006100')
R_FILL = PatternFill('solid', fgColor='FFC7CE'); R_FONT = Font(name=F, color='9C0006')
Y_FILL = PatternFill('solid', fgColor='FFEB9C'); Y_FONT = Font(name=F, color='9C5700')

def color_rows(ws, rng, col, rules):
    first = rng.split(':')[0]
    r1 = ''.join(ch for ch in first if ch.isdigit())
    for text, fill, font in rules:
        ws.conditional_formatting.add(rng, FormulaRule(formula=[f'${col}{r1}="{text}"'], fill=fill, font=font))

STAT = [('Bisa', G_FILL, G_FONT), ('Tidak Bisa', R_FILL, R_FONT), ('Sebagian', Y_FILL, Y_FONT)]

# Semua Kategori: warnai seluruh baris berdasar Status (kolom H)
for t in ws3.tables.values(): t.tableStyleInfo.showRowStripes = False
for i in range(2, len(rows) + 2): ws3.cell(i, 8).font = body
color_rows(ws3, f'A2:I{len(rows)+1}', 'H', STAT)

# Tidak Bisa Diisi: semua baris merah
for t in ws2.tables.values(): t.tableStyleInfo.showRowStripes = False
for i in range(2, len(bad) + 2):
    for j in range(1, 8): ws2.cell(i, j).fill = R_FILL

# Ringkasan per kategori utama: kolom Status
ws.cell(r0 + 1, 6, 'Status'); header_cells = ws.cell(r0 + 1, 6)
header_cells.font, header_cells.fill, header_cells.border = hdr_font, hdr_fill, box
for rr in range(first, last + 1):
    c = ws.cell(rr, 6, f'=IF(D{rr}=0,"Bisa",IF(C{rr}=0,"Tidak Bisa","Sebagian"))'); c.font = body; c.border = box
ws.cell(last + 1, 6).border = box
color_rows(ws, f'A{first}:F{last}', 'F', STAT)
ws.column_dimensions['F'].width = 13
ws['A8'] = 'Warna: hijau = semua bisa diisi · kuning = sebagian bisa · merah = tidak bisa sama sekali'
ws['A8'].font = Font(name=F, size=9, italic=True)

# Sheet baru: Rekap Subkategori
ws6 = wb.create_sheet('Rekap Subkategori', 1)
header(ws6, 1, ['Kategori Utama', 'Subkategori', 'Total', 'Bisa', 'Tidak Bisa', '% Tidak Bisa', 'Status'])
subs = sorted({(r_['l1'], r_['l2']) for r_ in rows}, key=lambda x: (x[0].lower(), x[1].lower()))
for i, (a, b) in enumerate(subs, 2):
    ws6.cell(i, 1, a); ws6.cell(i, 2, b)
    ws6.cell(i, 3, f"=COUNTIFS('Semua Kategori'!B:B,A{i},'Semua Kategori'!C:C,B{i})")
    ws6.cell(i, 4, f"=COUNTIFS('Semua Kategori'!B:B,A{i},'Semua Kategori'!C:C,B{i},'Semua Kategori'!H:H,\"Bisa\")")
    ws6.cell(i, 5, f"=COUNTIFS('Semua Kategori'!B:B,A{i},'Semua Kategori'!C:C,B{i},'Semua Kategori'!H:H,\"Tidak Bisa\")")
    ws6.cell(i, 6, f'=IF(C{i}=0,0,E{i}/C{i})').number_format = '0%'
    ws6.cell(i, 7, f'=IF(E{i}=0,"Bisa",IF(D{i}=0,"Tidak Bisa","Sebagian"))')
    for j in range(1, 8): ws6.cell(i, j).font = body; ws6.cell(i, j).border = box
n6 = len(subs) + 1
color_rows(ws6, f'A2:G{n6}', 'G', STAT)
ws6.auto_filter.ref = f'A1:G{n6}'
ws6.freeze_panes = 'C2'
ws6.cell(n6 + 2, 1, 'Warna: hijau = semua kategori produk di subkategori ini bisa diisi · kuning = sebagian · merah = tidak bisa sama sekali').font = Font(name=F, size=9, italic=True)
widths(ws6, [42, 52, 9, 9, 12, 13, 12])

# ================= KBLI per kategori =================
NM = json.load(open(ROOT + '/data/inaproc_nama_kbli.json'))
def kname(code, ver):
    if ver == '2025':
        if code in NM['k25']: return NM['k25'][code]
        if code in NM['k20']: return NM['k20'][code] + ' *'
    return NM['k20'].get(code, '(nama tidak ditemukan)')

def pretty(codes_str, ver):
    return '; '.join(f'{c} {kname(c, ver)}' for c in codes_str.split(', ') if c)

# Tambah kolom nama KBLI (2020) di Tidak Bisa Diisi & Semua Kategori
for wsx, data, col in ((ws2, bad, 8), (ws3, rows, 10)):
    h = wsx.cell(1, col, 'Daftar KBLI yang diterima (kode + nama, versi 2020)')
    h.font, h.fill, h.border = hdr_font, hdr_fill, box
    h.alignment = Alignment(wrap_text=True, vertical='center')
    for i, r_ in enumerate(data, 2):
        c = wsx.cell(i, col, pretty(r_['k20'], '2020')); c.font = body
        if wsx is ws2: c.fill = R_FILL
    wsx.column_dimensions[get_column_letter(col)].width = 90
    for t in wsx.tables.values():
        t.ref = f'A1:{get_column_letter(col)}{len(data) + 1}'
        t._initialise_columns()
        for tc, hc in zip(t.tableColumns, wsx[1]): tc.name = hc.value
ws3.conditional_formatting = type(ws3.conditional_formatting)()
color_rows(ws3, f'A2:J{len(rows)+1}', 'H', STAT)

# Rekap Subkategori: kolom KBLI yang diterima
sub_codes = collections.defaultdict(set)
for r_ in rows:
    for c in r_['k20'].split(', '):
        if c: sub_codes[(r_['l1'], r_['l2'])].add(c)
h = ws6.cell(1, 8, 'KBLI yang diterima (versi 2020) – cukup punya salah satu')
h.font, h.fill, h.border = hdr_font, hdr_fill, box; h.alignment = Alignment(wrap_text=True)
for i, key in enumerate(subs, 2):
    c = ws6.cell(i, 8, '; '.join(f'{x} {kname(x, "2020")}' for x in sorted(sub_codes[key]))); c.font = body; c.border = box
ws6.column_dimensions['H'].width = 110
ws6.conditional_formatting = type(ws6.conditional_formatting)()
color_rows(ws6, f'A2:H{n6}', 'G', STAT)
ws6.auto_filter.ref = f'A1:H{n6}'

# Ringkasan: kode KBLI per kategori utama
l1_codes = collections.defaultdict(set)
for r_ in rows:
    for c in r_['k20'].split(', '):
        if c: l1_codes[r_['l1']].add(c)
h = ws.cell(r0 + 1, 7, 'Kode KBLI yang diterima (versi 2020)')
h.font, h.fill, h.border = hdr_font, hdr_fill, box
for rr in range(first, last + 1):
    c = ws.cell(rr, 7, ', '.join(sorted(l1_codes[ws.cell(rr, 1).value]))); c.font = body; c.border = box
ws.column_dimensions['G'].width = 100
ws.conditional_formatting = type(ws.conditional_formatting)()
color_rows(ws, f'A{first}:G{last}', 'F', STAT)

# Sheet: KBLI per Kategori (1 baris = 1 kategori produk x 1 KBLI)
ws7 = wb.create_sheet('KBLI per Kategori', 4)
cols7 = ['Kategori Utama', 'Subkategori', 'Kategori Produk', 'Kode KBLI', 'Versi', 'Nama KBLI', 'Dimiliki Perusahaan', 'Status Kategori']
header(ws7, 1, cols7)
i = 2
for r_ in rows:
    cs = []
    for c in r_['k20'].split(', '):
        if c: cs.append((c, '2020'))
    for c in r_['k25'].split(', '):
        if c: cs.append((c, '2025'))
    for code, ver in cs:
        vals = [r_['l1'], r_['l2'], r_['l3'], code, ver, kname(code, ver),
                'Ya' if f'{code}|{ver}' in seller_set else 'Tidak', 'Bisa' if r_['ok'] else 'Tidak Bisa']
        for j, v in enumerate(vals, 1): ws7.cell(i, j, v).font = body
        i += 1
n7 = i - 1
color_rows(ws7, f'A2:H{n7}', 'H', STAT)
ws7.conditional_formatting.add(f'G2:G{n7}', FormulaRule(formula=['$G2="Ya"'], fill=PatternFill('solid', fgColor='00B050'), font=Font(name=F, bold=True, color='FFFFFF')))
ws7.auto_filter.ref = f'A1:H{n7}'
ws7.freeze_panes = 'D2'
widths(ws7, [36, 40, 44, 11, 7, 60, 12, 13])

# Sheet: Daftar KBLI (master)
ws8 = wb.create_sheet('Daftar KBLI', 5)
header(ws8, 1, ['Kode KBLI', 'Versi', 'Nama KBLI', 'Dimiliki Perusahaan', 'Jumlah kategori produk yang menerima', 'Jumlah kategori "Tidak Bisa" yang akan terbuka'])
tot = collections.Counter(); unl = collections.Counter()
for r_ in rows:
    for ver, key in (('2020', 'k20'), ('2025', 'k25')):
        for c in r_[key].split(', '):
            if c:
                tot[(c, ver)] += 1
                if not r_['ok']: unl[(c, ver)] += 1
keys = sorted(tot, key=lambda x: (-unl[x], x[1], x[0]))
for i, (c, ver) in enumerate(keys, 2):
    vals = [c, ver, kname(c, ver), 'Ya' if f'{c}|{ver}' in seller_set else 'Tidak', tot[(c, ver)], unl[(c, ver)]]
    for j, v in enumerate(vals, 1): ws8.cell(i, j, v).font = body; ws8.cell(i, j).border = box
n8 = len(keys) + 1
ws8.conditional_formatting.add(f'A2:F{n8}', FormulaRule(formula=['$D2="Ya"'], fill=G_FILL, font=G_FONT))
ws8.auto_filter.ref = f'A1:F{n8}'
ws8.freeze_panes = 'A2'
ws8.cell(n8 + 2, 1, 'Hijau = KBLI yang sudah dimiliki perusahaan. Diurutkan dari KBLI yang paling banyak membuka kategori "Tidak Bisa". '
         '* = nama versi 2025 tidak tersedia di INAPROC, dipakai nama versi 2020. Sumber nama: master KBLI INAPROC.').font = Font(name=F, size=9, italic=True)
widths(ws8, [11, 7, 75, 12, 20, 24])

# ================= Rekomendasi Produk =================
have = json.load(open(ROOT + '/data/produk_existing_pt_kig.json'))
seller_name = {k.split('|')[0]: v for k, v in seller}
have_l2 = {(r_['l1'], r_['l2']) for r_ in rows if r_['l3'] in have}
have_l1 = {r_['l1'] for r_ in rows if r_['l3'] in have}
SPECIAL_L1 = {'Alat Kesehatan': 'Umumnya butuh izin edar alat kesehatan (AKL/AKD)',
              'Alat Penunjang Pelayanan Kesehatan': 'Cek kebutuhan izin edar alat kesehatan',
              'Jasa Bidang Kesehatan': 'Jasa khusus bidang kesehatan',
              'Perangkat Lunak/Software': 'Biasanya perlu status reseller/partner resmi',
              'Pesawat Angkut': 'Alat berat – modal & dukungan purna jual besar',
              'Pesawat Angkat': 'Alat berat – modal & dukungan purna jual besar',
              'Pesawat Tenaga dan Produksi': 'Alat berat – modal & dukungan purna jual besar',
              'Pesawat/Peralatan Konstruksi Lainnya': 'Peralatan konstruksi – modal besar'}
for k in L1:
    if k.startswith('Peralatan Bidang') or k.startswith('Jasa Bidang') and k not in SPECIAL_L1:
        SPECIAL_L1.setdefault(k, 'Peralatan/jasa teknis BMKG – sangat spesifik')
TIER = {1: 'Prioritas 1 – lengkapi subkategori yang sudah Anda isi',
        2: 'Prioritas 2 – subkategori baru di kategori utama yang sudah Anda isi',
        3: 'Prioritas 3 – kategori utama baru'}
cand = []
for r_ in rows:
    if not r_['ok'] or r_['l3'] in have: continue
    t = 1 if (r_['l1'], r_['l2']) in have_l2 else (2 if r_['l1'] in have_l1 else 3)
    m = [x.split(' (')[0] for x in r_['match'].split(', ') if x]
    note = SPECIAL_L1.get(r_['l1'], '')
    if r_['l2'].startswith('Alat Uji') or r_['l2'].startswith('Alat Kalibrasi'):
        note = note or 'Alat uji/kalibrasi – spesifik'
    cand.append((t, r_, m, note))
cand.sort(key=lambda x: (x[0], x[1]['l1'].lower(), x[1]['l2'].lower(), x[1]['l3'].lower()))

ws9 = wb.create_sheet('Rekomendasi Produk', 1)
ws9['A1'] = 'Rekomendasi Produk yang Bisa Ditambahkan'; ws9['A1'].font = title
ws9['A2'] = (f'Dari {sum(1 for r_ in rows if r_["ok"])} kategori berstatus "Bisa", {len(have)} sudah Anda isi ({sum(have.values())} produk). '
             f'Sisa {len(cand)} kategori di bawah ini belum punya produk, diurutkan berdasarkan prioritas. '
             'Prioritas disusun dari kedekatan dengan produk yang sudah Anda jual (bukan data permintaan pasar).')
ws9['A2'].font = Font(name=F, size=9, italic=True); ws9['A2'].alignment = Alignment(wrap_text=True, vertical='top')
ws9.merge_cells('A2:H2'); ws9.row_dimensions[2].height = 30
HR = 4
header(ws9, HR, ['Prioritas', 'Kategori Utama', 'Subkategori', 'Kategori Produk', 'Jenis', 'KBLI Anda yang memenuhi', 'Nama KBLI', 'Catatan'])
P_FILL = {1: PatternFill('solid', fgColor='C6EFCE'), 2: PatternFill('solid', fgColor='E2EFDA'), 3: PatternFill('solid', fgColor='F2F2F2')}
for i, (t, r_, m, note) in enumerate(cand, HR + 1):
    vals = [TIER[t], r_['l1'], r_['l2'], r_['l3'], r_['jenis'], ', '.join(m), '; '.join(seller_name.get(x, '') for x in m), note]
    for j, v in enumerate(vals, 1):
        c = ws9.cell(i, j, v); c.font = body; c.fill = P_FILL[t]
    if note: ws9.cell(i, 8).font = Font(name=F, size=10, color='9C5700', italic=True)
n9 = HR + len(cand)
ws9.auto_filter.ref = f'A{HR}:H{n9}'
ws9.freeze_panes = f'B{HR+1}'
widths(ws9, [44, 34, 38, 44, 9, 16, 60, 44])

# Ringkasan rekomendasi per subkategori (ditaruh di Ringkasan, kolom I dst)
rc = collections.Counter((t, r_['l1'], r_['l2']) for t, r_, m, note in cand)
c0 = 9
ws.cell(r0, c0, 'Subkategori yang direkomendasikan (Prioritas 1 & 2)').font = Font(name=F, size=12, bold=True)
header_row = r0 + 1
for j, h in enumerate(['Prioritas', 'Kategori Utama', 'Subkategori', 'Jumlah kategori produk'], c0):
    c = ws.cell(header_row, j, h); c.font, c.fill, c.border = hdr_font, hdr_fill, box
rr = header_row + 1
for (t, a, b), n in sorted(rc.items(), key=lambda x: (x[0][0], -x[1], x[0][1])):
    if t > 2: continue
    for j, v in enumerate([t, a, b, n], c0):
        c = ws.cell(rr, j, v); c.font = body; c.border = box; c.fill = P_FILL[t]
    rr += 1
for col, w in zip('IJKL', [10, 30, 46, 12]): ws.column_dimensions[col].width = w

# Produk Saya
ws10 = wb.create_sheet('Produk Saya')
header(ws10, 1, ['Kategori Utama', 'Subkategori', 'Kategori Produk', 'Jumlah Produk', 'Status KBLI kategori', 'Catatan'])
mine = sorted([r_ for r_ in rows if r_['l3'] in have], key=lambda r_: (r_['l1'], r_['l2'], r_['l3']))
for i, r_ in enumerate(mine, 2):
    st = 'Bisa' if r_['ok'] else 'Tidak Bisa'
    note = '' if r_['ok'] else 'Produk sudah ada, tapi KBLI Anda saat ini tidak sesuai kategori ini – cek ulang/pindahkan kategori'
    for j, v in enumerate([r_['l1'], r_['l2'], r_['l3'], have[r_['l3']], st, note], 1):
        c = ws10.cell(i, j, v); c.font = body; c.border = box
color_rows(ws10, f'A2:F{len(mine)+1}', 'E', STAT)
ws10.cell(len(mine) + 2, 3, 'TOTAL').font = bold
ws10.cell(len(mine) + 2, 4, f'=SUM(D2:D{len(mine)+1})').font = bold
widths(ws10, [26, 40, 46, 14, 18, 80])

# Saran KBLI lama digantikan Daftar KBLI
del wb['Saran KBLI']

wb.save(ROOT + '/output/Rekap_Kategori_INAPROC_KBLI.xlsx')
print('subkategori', len(subs), 'kbli rows', n7, 'master', len(keys))
print(len(rows), len(bad), len(cnt))
