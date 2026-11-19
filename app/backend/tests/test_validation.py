"""Validator menolak kasus contoh (kriteria selesai #3) + hitungan kelayakan (#4) + 15 template (#2)."""
from sqlmodel import select

from app.models import Company, TemplateSchema
from app.services import kelayakan
from app.services.defaults import apply_defaults
from app.services.validator import Ctx, validate_row


def _schema(session, slug="busi-mobil"):
    comp = session.exec(select(Company)).first()
    return session.exec(select(TemplateSchema).where(TemplateSchema.company_id == comp.id, TemplateSchema.slug == slug)).first()


def _base(sc):
    d, _ = apply_defaults(sc, {
        "D": "Busi Iridium Mobil Bensin", "E": "https://i.imgur.com/abc.png", "X": 10, "Y": "PCS",
        "AC": 85000, "AD": 60, "V": "JPN"}, "Impor")
    return d


def _msgs(sc, d, ctx=None):
    return [(i["col"], i["msg"]) for i in validate_row(sc, d, ctx or Ctx()) if i["level"] == "error"]


def test_data_valid_tanpa_error(session):
    sc = _schema(session)
    assert _msgs(sc, _base(sc)) == []


def test_nama_8_karakter(session):
    sc = _schema(session)
    d = _base(sc); d["D"] = "Busi 123"
    assert any(c == "D" and "8 karakter" in m for c, m in _msgs(sc, d))


def test_harga_dengan_pemisah(session):
    sc = _schema(session)
    d = _base(sc); d["AC"] = "85.000"
    assert any(c == "AC" for c, _ in _msgs(sc, d))


def test_preorder_tanpa_hari(session):
    sc = _schema(session)
    d = _base(sc); d["AA"] = "Aktif"
    assert any(c == "AB" for c, _ in _msgs(sc, d))


def test_foto_jpg(session):
    sc = _schema(session)
    d = _base(sc); d["E"] = "https://i.imgur.com/abc.jpg"
    assert any(c == "E" and ".png" in m for c, m in _msgs(sc, d))


def test_satuan_di_luar_daftar(session):
    sc = _schema(session)
    d = _base(sc); d["Y"] = "KILOGRAM-X"
    assert any(c == "Y" for c, _ in _msgs(sc, d))


def test_kbki_bukan_milik_kategori(session):
    sc = _schema(session)
    d = _base(sc); d["Q"] = "4912903001"
    assert any(c == "Q" for c, _ in _msgs(sc, d))


def test_ppnbm_aktif_wajib_npq(session):
    sc = _schema(session)
    d = _base(sc); d["M"] = "Aktif"
    cols = {c for c, _ in _msgs(sc, d)}
    assert {"N", "O", "P"} <= cols


def test_duplikat_nama(session):
    sc = _schema(session)
    d = _base(sc)
    ctx = Ctx(name_counts={"busi iridium mobil bensin": 2})
    assert any("duplikat" in m for _, m in _msgs(sc, d, ctx))


def test_kolom_u_dan_kosongkan_tidak_diekspor(session):
    from app.routers.batches import sanitize
    from app.models import Batch
    sc = _schema(session, "jasa-servis-mobil")
    out = sanitize(sc, {"D": "Servis Berkala Mobil", "U": "LOCAL", "AD": 100, "AH": "STANDARD"}, Batch(name="x", created_by=1, company_id=1))
    assert "U" not in out and "AD" not in out and "AH" not in out


def test_kbki_otomatis(session):
    sc = _schema(session, "busi-mobil")
    d, guess = apply_defaults(sc, {"D": "Busi X Mobil"})
    assert d["Q"] == "4691001002" and guess is False
    sc2 = _schema(session, "rem-mobil")
    d2, guess2 = apply_defaults(sc2, {"D": "Kampas rem cakram depan"})
    assert guess2 is True and d2["Q"] == "4912903003"


def test_kelayakan_snapshot(session):
    comp = session.exec(select(Company)).first()
    t = kelayakan.build_tree(session, comp.id)["totals"]
    assert t["kategori_bisa"] == 756 and t["kategori_tidak_bisa"] == 2114
    assert t["utama_dengan_bisa"] == 29


def test_15_template_terdeteksi(session):
    comp = session.exec(select(Company)).first()
    ts = session.exec(select(TemplateSchema).where(TemplateSchema.company_id == comp.id)).all()
    assert len(ts) == 15
    assert [t.slug for t in ts if t.jenis == "Jasa"] == ["jasa-servis-mobil"]
    assert sum(1 for t in ts if t.jenis == "Barang") == 14
    for t in ts:
        assert t.category_uuid and t.category_id, t.slug
        assert t.institution_id == comp.institution_id
