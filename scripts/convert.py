"""Pindahkan data dari Form ke template resmi INAPROC + validasi + zip.
Pemakaian: python3 convert.py FORM.xlsx OUTDIR STATUS(Tayang|Tidak Tayang) [PLACEHOLDER_IMG_URL]"""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)

import sys, json, os, re, shutil, zipfile
from openpyxl import load_workbook

FORM, OUT, STATUS = sys.argv[1], sys.argv[2], sys.argv[3]
PLACEHOLDER = sys.argv[4] if len(sys.argv) > 4 else None
info = json.load(open(ROOT + '/templates/tpl_info.json'))
CAT = json.load(open(ROOT + '/templates/cat_names.json'))
NAME2SLUG = {v: k for k, v in CAT.items()}
os.makedirs(OUT, exist_ok=True)
issues, report = [], []

def num(v):
    if v is None or v == '': return None
    if isinstance(v, (int, float)): return int(v) if float(v).is_integer() else v
    s = re.sub(r'[^\d]', '', str(v)); return int(s) if s else None

def img(v, where):
    if not v: return None
    v = str(v).strip()
    if v.startswith('http'):
        if not v.lower().endswith('.png') and 'drive.google.com' not in v:
            issues.append(f'{where}: link foto tidak berakhiran .png → {v}')
        return v
    if PLACEHOLDER:
        issues.append(f'{where}: foto "{v}" belum punya link publik – sementara diisi link contoh INAPROC, WAJIB diganti sebelum unggah sungguhan')
        return PLACEHOLDER
    issues.append(f'{where}: foto "{v}" belum punya link publik .png'); return None

def pick_kbki(slug, given, text):
    opts = info[slug]['kbki']
    if given:
        code = str(given).split(' - ')[0].strip()
        if code in [o[0] for o in opts]: return code
        issues.append(f'{text}: KBKI {code} tidak tersedia untuk kategori ini – dipilih otomatis')
    if len(opts) == 1: return opts[0][0]
    t = text.lower()
    kw = {'cakram': 'Rem cakram', 'kampas': 'Rem cakram', 'tromol': 'Tromol rem', 'sepatu': 'Sepatu rem', 'servo': 'Rem servo',
          'tubeless': 'Tubeless', 'truk': 'truk', 'pelek': 'Pelek', 'velg': 'Pelek', 'dop': 'Penutup pelek',
          'busi': 'Busi', 'kopling': 'Kopling', 'knalpot': 'Knalpot', 'fan belt': 'Fan belt', 'mounting': 'Engine mounting',
          'klakson': 'Klakson', 'koil': 'koil', 'piston': 'Piston', 'filter': 'filter'}
    for k, want in kw.items():
        if k in t:
            for c, d in opts:
                if want.lower() in d.lower(): return c
    issues.append(f'{text}: KBKI dipilih default ({opts[0][1]}) – mohon dicek')
    return opts[0][0]

src = load_workbook(FORM, data_only=True)
rows_by_slug = {}
# Barang
for r in src['Barang'].iter_rows(min_row=2, values_only=True):
    if not r[2] or str(r[0]).upper() == 'CONTOH': continue
    rows_by_slug.setdefault(NAME2SLUG.get(r[1], '?'), []).append(('B', r))
for r in src['Jasa Servis Mobil'].iter_rows(min_row=2, values_only=True):
    if not r[1] or str(r[0]).upper() == 'CONTOH': continue
    rows_by_slug.setdefault('jasa-servis-mobil', []).append(('J', r))

def L(col):  # letter -> index
    from openpyxl.utils import column_index_from_string as c; return c(col)

made = []
for slug, items in rows_by_slug.items():
    if slug == '?':
        for _, r in items: issues.append(f'{r[2]}: kategori "{r[1]}" tidak dikenal – dilewati')
        continue
    fn = info[slug]['file']
    wb = load_workbook(ROOT + '/templates/' + fn)
    ws = wb.worksheets[0]
    ws.delete_rows(7, 3)  # hapus baris petunjuk & contoh (7-9)
    for i, (kind, r) in enumerate(items):
        R = 7 + i
        v = {}
        if kind == 'B':
            (no, kat, nama, tipe, spek, desk, garansi, harga, ppn, stok, sat, minb, berat, p, l, t, pd, tk, bb, neg, po, poh,
             f1, f2, f3, f4, f5, vid, kbki, cat) = r[:30]
            where = f'[{CAT[slug]}] {nama}'
            v.update({'AD': num(berat), 'AE': num(p), 'AF': num(l), 'AG': num(t), 'AH': 'STANDARD',
                      'AJ': tipe, 'AK': spek, 'AL': garansi})
            fotos = [f1, f2, f3, f4, f5]
        else:
            (no, nama, desk, rincian, garansi, harga, ppn, stok, sat, minb, pd, tk, bb, neg, personil, biaya_lain, po, poh,
             f1, f2, f3, cat) = r[:22]
            where = f'[Jasa Servis Mobil] {nama}'
            kbki = None; vid = None
            v.update({'AJ': rincian, 'AK': garansi, 'AM': personil, 'AN': biaya_lain})
            fotos = [f1, f2, f3, None, None]
        nama = str(nama).strip()
        if not 10 <= len(nama) <= 100: issues.append(f'{where}: panjang nama {len(nama)} karakter (harus 10–100)')
        v.update({'C': STATUS, 'D': nama, 'J': vid, 'K': desk, 'L': ppn or '12%', 'M': 'Tidak Aktif',
                  'Q': pick_kbki(slug, kbki, nama), 'R': pd, 'S': tk, 'T': bb,
                  'V': str(neg).split(' - ')[0] if neg else None, 'W': 'Tidak Aktif',
                  'X': num(stok), 'Y': sat, 'Z': num(minb) or 1,
                  'AA': 'Aktif' if str(po).lower() == 'ya' else 'Tidak Aktif',
                  'AB': num(poh) if str(po).lower() == 'ya' else None, 'AC': num(harga)})
        for k, f in zip('EFGHI', fotos): v[k] = img(f, where)
        # validasi wajib
        req = ['D', 'E', 'L', 'Q', 'R', 'S', 'T', 'V', 'X', 'Y', 'Z', 'AC'] + (['AD', 'AH'] if kind == 'B' else [])
        for k in req:
            if v.get(k) in (None, '', 0): issues.append(f'{where}: kolom wajib {k} ({ws[k + "5"].value}) kosong')
        if v['AA'] == 'Aktif' and not v['AB']: issues.append(f'{where}: Pre Order aktif tapi jumlah hari kosong')
        for k, val in v.items():
            if val is not None: ws.cell(R, L(k), val)
        report.append((CAT.get(slug, 'Jasa Servis Mobil'), nama, v['AC'], v['Q']))
    out = os.path.join(OUT, fn)
    wb.save(out); made.append(out)

zp = os.path.join(OUT, 'unggah_inaproc.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in made: z.write(f, os.path.basename(f))
print('FILES', len(made)); [print(' ', os.path.basename(f)) for f in made]
print('ROWS'); [print(' ', x) for x in report]
print('ISSUES'); [print(' -', x) for x in issues]
print('ZIP', zp, os.path.getsize(zp))
