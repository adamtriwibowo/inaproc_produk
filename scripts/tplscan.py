import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(ROOT, 'output'), exist_ok=True)
import glob, re, json
from openpyxl import load_workbook
out={}
for f in sorted(glob.glob(ROOT + '/templates/*Unggah_Produk_Sekaligus*.xlsx')):
    slug=re.search(r'Sekaligus_-_(.+?)_-_Format',f).group(1)
    wb=load_workbook(f); ws=wb.worksheets[0]
    cols=[]
    sec=None
    for c in range(1,ws.max_column+1):
        if ws.cell(4,c).value: sec=ws.cell(4,c).value
        cols.append((c,sec,ws.cell(5,c).value,ws.cell(6,c).value,ws.cell(7,c).value))
    dvs={}
    for dv in ws.data_validations.dataValidation:
        for rng in str(dv.sqref).split():
            col=re.match(r'[A-Z]+',rng).group(0); dvs[col]=str(dv.formula1)
    kbki=[[x.value for x in r] for r in wb['Daftar KBKI'].iter_rows(min_row=2) if r[0].value]
    out[slug]=dict(file=os.path.basename(f),sheets=wb.sheetnames,cat=ws['B2'].value,ncol=ws.max_column,cols=cols,dvs=dvs,kbki=kbki)
json.dump(out,open(ROOT + '/templates/tpl_info.json','w'),default=str)
base=out['spare-part-mobil-lainnya']['cols']
for s,v in out.items():
    hdr=[c[2] for c in v['cols']]
    diff=[(c[0],c[1],c[2],c[3]) for c in v['cols'] if c[0]>35 or (c[0]<=len(base) and base[c[0]-1][2]!=c[2])]
    print('##',s,v['ncol'],len(v['kbki']),v['sheets'][1:])
    print('   ',diff)
