"""Golden test: Form_Data_Produk_DUMMY.xlsx -> template terisi harus identik dengan file yang sudah diterima INAPROC."""
import io
from types import SimpleNamespace

from openpyxl import load_workbook
from sqlmodel import select

from app import config
from app.models import Company, TemplateSchema
from app.services.defaults import apply_defaults
from app.services.exporter import fill_template
from app.services.form_io import import_form

PLACEHOLDER = "https://i.imgur.com/ErNwW2p.png"


def _grid(ws, rows):
    return [[ws.cell(r, c).value for c in range(1, ws.max_column + 1)] for r in range(1, rows + 1)]


def test_golden_export_identik(session):
    comp = session.exec(select(Company)).first()
    schemas = session.exec(select(TemplateSchema).where(TemplateSchema.company_id == comp.id)).all()
    rows, issues = import_form((config.GOLDEN_DIR / "Form_Data_Produk_DUMMY.xlsx").read_bytes(), schemas)
    assert len(rows) == 3, issues
    photos = {n: SimpleNamespace(public_url=PLACEHOLDER)
              for n in ("dummy-busi-01.png", "dummy-rem-01.png", "dummy-servis-01.png")}
    by_schema: dict = {}
    for sc, d in rows:
        d, _ = apply_defaults(sc, d, "Lokal")
        # preset Lokal hanya default; form dummy mengisi PDN & negara sendiri
        by_schema.setdefault(sc.id, (sc, []))[1].append(d)
    assert len(by_schema) == 3
    golden_files = {p.name: p for p in config.GOLDEN_DIR.glob("*Unggah_Produk*.xlsx")}
    for sc, data_rows in by_schema.values():
        out = fill_template(sc, data_rows, "Tidak Tayang", photos)
        assert sc.filename in golden_files, sc.filename
        wo = load_workbook(io.BytesIO(out))
        wg = load_workbook(golden_files[sc.filename])
        assert wo.sheetnames == wg.sheetnames
        a, b = wo.worksheets[0], wg.worksheets[0]
        assert a.max_column == b.max_column
        assert _grid(a, 8) == _grid(b, 8), sc.filename
        for name in wg.sheetnames[1:]:   # sheet pendukung
            assert _grid(wo[name], wg[name].max_row) == _grid(wg[name], wg[name].max_row), name
