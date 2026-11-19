"""Multi-perusahaan, role per perusahaan, alur batch & ekspor (kriteria #5, #5b)."""
import io
import json

import pytest
from openpyxl import load_workbook

from app import config
from tests.conftest import login

PW = "Passw0rd-123"
KIG = 1


@pytest.fixture(scope="module")
def world(client, admin_headers):
    h = admin_headers
    r = client.post("/api/admin/companies", json={"name": "PT Bravo Niaga", "institution_id": "01TESTBRAVO0000000000000001"}, headers=h)
    assert r.status_code == 200, r.text
    B = r.json()["id"]
    # KBLI perusahaan B: hanya 46511 -> kategori suku cadang mobil "Tidak Bisa"
    assert client.post(f"/api/companies/{B}/kbli", json={"code": "46511", "version": "2020"}, headers=h).status_code == 200
    users = {}
    for key, email in (("opA", "opa@t.l"), ("revA", "reva@t.l"), ("admA", "adma@t.l"), ("opB", "opb@t.l"), ("mix", "mix@t.l")):
        assert client.post("/api/admin/users", json={"email": email, "password": PW}, headers=h).status_code == 200
        users[key] = email
    for key, cid, role in (("opA", KIG, "operator"), ("revA", KIG, "reviewer"), ("admA", KIG, "admin"),
                           ("opB", B, "operator"), ("mix", KIG, "operator"), ("mix", B, "reviewer")):
        r = client.put("/api/admin/memberships", json={"user_id": _uid(client, h, users[key]), "company_id": cid, "role": role}, headers=h)
        assert r.status_code == 200, r.text
    H = {k: login(client, e, PW) for k, e in users.items()}
    return {"B": B, "H": H, "admin": h}


def _uid(client, h, email):
    return next(u["id"] for u in client.get("/api/admin/users", headers=h).json() if u["email"] == email)


def test_isolasi_data_perusahaan(client, world):
    H, B = world["H"], world["B"]
    # pengguna hanya-A tidak bisa membaca apa pun milik B
    for path in ("", "/kelayakan/tree", "/batches", "/templates", "/kbli", "/dashboard"):
        assert client.get(f"/api/companies/{B}{path}", headers=H["opA"]).status_code == 404, path
    assert client.post(f"/api/companies/{B}/batches", json={"name": "x"}, headers=H["opA"]).status_code == 404


def test_batch_lintas_perusahaan_404(client, world):
    H, B = world["H"], world["B"]
    r = client.post(f"/api/companies/{B}/batches", json={"name": "Batch B"}, headers=H["opB"])
    bid = r.json()["id"]
    # batch B diakses lewat URL perusahaan A -> 404
    assert client.get(f"/api/companies/{KIG}/batches/{bid}", headers=H["opA"]).status_code == 404
    assert client.get(f"/api/companies/{KIG}/batches/{bid}", headers=H["admA"]).status_code == 404


def test_kelayakan_berbeda_per_perusahaan(client, world):
    H, B = world["H"], world["B"]
    ta = client.get(f"/api/companies/{KIG}/kelayakan/tree", headers=H["opA"]).json()["totals"]
    tb = client.get(f"/api/companies/{B}/kelayakan/tree", headers=H["opB"]).json()["totals"]
    assert ta["kategori_bisa"] == 756 and tb["kategori_bisa"] != ta["kategori_bisa"]

    def busi(c):
        tree = client.get(f"/api/companies/{c}/kelayakan/tree", headers=H["mix"]).json()["tree"]
        for n1 in tree:
            for n2 in n1["children"]:
                for x in n2["children"]:
                    if x["name"] == "Busi Mobil":
                        return x["ok"]
    assert busi(KIG) is True and busi(B) is False


def test_template_perusahaan_lain_ditolak(client, world):
    H, B = world["H"], world["B"]
    f = next(config.TEMPLATES_SRC.glob("*busi-mobil*.xlsx"))
    raw = f.read_bytes()
    # template ber-Institution ID KIG diunggah ke B -> ditolak
    r = client.post(f"/api/companies/{B}/templates", files={"files": (f.name, raw)}, headers=world["admin"])
    assert r.json()["ditolak"] and "perusahaan lain" in r.json()["ditolak"][0]["alasan"]
    # template ber-Institution ID B diunggah ke KIG -> ditolak
    wb = load_workbook(io.BytesIO(raw))
    wb.worksheets[0]["B1"] = "01TESTBRAVO0000000000000001"
    buf = io.BytesIO(); wb.save(buf)
    r = client.post(f"/api/companies/{KIG}/templates", files={"files": (f.name, buf.getvalue())}, headers=H["admA"])
    assert r.json()["ditolak"] and "perusahaan lain" in r.json()["ditolak"][0]["alasan"]


def test_operator_tidak_bisa_upload_template(client, world):
    f = next(config.TEMPLATES_SRC.glob("*busi-mobil*.xlsx"))
    r = client.post(f"/api/companies/{KIG}/templates", files={"files": (f.name, f.read_bytes())}, headers=world["H"]["opA"])
    assert r.status_code == 403


def test_import_kbli_check_institution_harus_sama(client, world):
    payload = json.dumps({"institutionId": "SALAH", "seller": [], "leaves": []}).encode()
    r = client.post(f"/api/companies/{KIG}/kbli/import-check", files={"file": ("x.json", payload)}, headers=world["H"]["admA"])
    assert r.status_code == 400 and "institutionId" in r.json()["detail"]


def test_menu_role_mengikuti_perusahaan(client, world):
    H, B = world["H"], world["B"]
    me = client.get("/api/auth/me", headers=H["mix"]).json()
    roles = {m["company_id"]: m["role"] for m in me["memberships"]}
    assert roles == {KIG: "operator", B: "reviewer"}
    assert client.post(f"/api/companies/{KIG}/batches/1/approve", headers=H["mix"]).status_code == 403   # operator di A
    # reviewer di B boleh (batch tak ada -> 404, bukan 403)
    assert client.post(f"/api/companies/{B}/batches/9999/approve", headers=H["mix"]).status_code == 404


FORM = config.GOLDEN_DIR / "Form_Data_Produk_DUMMY.xlsx"


def test_alur_batch_dan_ekspor(client, world):
    H = world["H"]
    base = f"/api/companies/{KIG}/batches"
    r = client.post(base, json={"name": "Uji Golden", "is_test": True}, headers=H["opA"])
    b = r.json(); bid = b["id"]
    assert b["name"].startswith("[DUMMY]")
    r = client.post(f"{base}/{bid}/import-form", files={"file": ("f.xlsx", FORM.read_bytes())}, headers=H["opA"])
    assert r.json()["diimpor"] == 3
    # foto belum diunggah -> error; unggah foto dari folder golden (dicocokkan lewat nama file)
    assert client.post(f"{base}/{bid}/submit", headers=H["opA"]).status_code == 422
    pngs = sorted(config.GOLDEN_DIR.glob("dummy-*.png"))
    r = client.post(f"{base}/{bid}/photos", files=[("files", (p.name, p.read_bytes())) for p in pngs], headers=H["opA"])
    assert len(r.json()["diunggah"]) == 3 and all(x["cocok_dengan"] for x in r.json()["diunggah"]), r.text
    assert all(x["width"] == 700 and x["size"] < 1024 * 1024 for x in r.json()["diunggah"])
    # foto sudah diproses tetapi belum punya link publik = peringatan; submit boleh, ekspor harus meminta link
    r = client.post(f"{base}/{bid}/submit", headers=H["opA"])
    assert r.status_code == 200, r.text
    # operator tidak boleh menyetujui / mengekspor
    assert client.post(f"{base}/{bid}/approve", headers=H["opA"]).status_code == 403
    assert client.post(f"{base}/{bid}/export", json={"confirm": True}, headers=H["opA"]).status_code == 403
    # ekspor sebelum disetujui ditolak
    assert client.post(f"{base}/{bid}/export", json={"confirm": True}, headers=H["revA"]).status_code == 403
    # reviewer menyetujui
    assert client.post(f"{base}/{bid}/approve", headers=H["revA"]).status_code == 200
    # tanpa konfirmasi -> 400
    assert client.post(f"{base}/{bid}/export", json={"confirm": False}, headers=H["revA"]).status_code == 400
    # foto belum punya link -> 422
    assert client.post(f"{base}/{bid}/export", json={"confirm": True}, headers=H["revA"]).status_code == 422
    r = client.post(f"{base}/{bid}/export", json={"confirm": True, "placeholder_url": "https://i.imgur.com/ErNwW2p.png"}, headers=H["revA"])
    assert r.status_code == 200, r.text
    files = r.json()["files"]
    zip_item = next(f for f in files if f["name"].endswith(".zip"))
    z = client.get(zip_item["url"], headers=H["revA"])
    import zipfile
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert len(names) == 3 and all("/" not in n for n in names)
    assert any(f["name"] == "laporan_batch.xlsx" for f in files)
    assert client.get(f"{base}/{bid}", headers=H["revA"]).json()["batch"]["status"] == "Diekspor"


def test_reviewer_tidak_menyetujui_batch_sendiri(client, world):
    H, B = world["H"], world["B"]
    # 'mix' adalah Reviewer di B tetapi tidak bisa membuat batch di B (hanya reviewer) -> 403
    assert client.post(f"/api/companies/{B}/batches", json={"name": "x"}, headers=H["mix"]).status_code == 403
    # Admin KIG membuat batch lalu mengajukan; reviewer = pembuat tidak mungkin lewat role, uji langsung via model
    from app.db import session_scope
    from app.models import Batch
    with session_scope() as s:
        uid = _uid(client, world["admin"], "reva@t.l")
        b = Batch(company_id=KIG, name="Milik reviewer", status="Diajukan", created_by=uid)
        s.add(b); s.commit(); s.refresh(b); bid = b.id
    assert client.post(f"/api/companies/{KIG}/batches/{bid}/approve", headers=H["revA"]).status_code == 403


def test_hanya_aksi_editable(client, world):
    H = world["H"]
    base = f"/api/companies/{KIG}/batches"
    bid = client.post(base, json={"name": "Edit"}, headers=H["opA"]).json()["id"]
    sch = client.get(f"/api/companies/{KIG}/templates", headers=H["opA"]).json()
    busi = next(t for t in sch if t["slug"] == "busi-mobil")
    r = client.put(f"{base}/{bid}/rows", json={"rows": [{"schema_id": busi["id"], "data": {"D": "Busi Iridium Test Satu", "AC": "85.000"}}]}, headers=H["opA"])
    assert r.status_code == 200
    row = r.json()["rows"][0]
    assert row["data"]["Q"] == "4691001002" and row["data"]["L"] == "12%" and row["data"]["AH"] == "STANDARD"
    assert any(i["col"] == "AC" for i in row["issues"])
    # tidak boleh submit karena error
    assert client.post(f"{base}/{bid}/submit", headers=H["opA"]).status_code == 422
    # schema milik perusahaan lain tidak bisa dipakai
    assert client.put(f"{base}/{bid}/rows", json={"rows": [{"schema_id": 99999, "data": {}}]}, headers=H["opA"]).status_code == 404
