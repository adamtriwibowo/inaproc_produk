"""Client OpenRouter palsu untuk test: respons berformat OpenAI-compatible (content JSON, usage.cost, provider)."""
import json
import re

from app.ai.ai_client import AiError, AiResult


def _text_of(messages) -> str:
    out = []
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, list):
            out += [p.get("text", "") for p in c if isinstance(p, dict)]
    return "\n".join(out)


class FakeProvider:
    def __init__(self):
        self.calls: list = []
        self.fail_models: set = set()
        self.hallucinate = False       # mengarang berat yang tidak ada di sumber
        self.bad_category = False      # memilih kategori di luar kandidat
        self.bad_kbki = False          # memilih KBKI di luar daftar template
        self.models = []               # untuk /models
        self.enum_sizes: list = []

    def list_models(self):
        return self.models

    def list_image_models(self):
        return []

    def chat(self, *, model, messages, fallbacks=None, response_format=None, **kw):
        name = (response_format or {}).get("json_schema", {}).get("name", "")
        self.calls.append({"model": model, "name": name, "messages": messages, "fallbacks": fallbacks, "kw": kw})
        if model in self.fail_models:
            raise AiError("OpenRouter tidak merespons dengan baik (HTTP 500).")
        text = _text_of(messages)
        if name == "ekstraksi_produk":
            body = self._extract(text)
        elif name == "klasifikasi":
            schema = response_format["json_schema"]["schema"]
            self.enum_sizes.append(len(schema["properties"]["hasil"]["items"]["properties"]["kategori_id"]["enum"]))
            body = self._classify(text)
        else:
            body = {}
        return AiResult(content=json.dumps(body), model=model, provider="FakeProvider", prompt_tokens=120, completion_tokens=60, cost_usd=0.002)

    @staticmethod
    def _field(v, quote=None):
        return {"nilai": v, "kutipan": quote if v is not None else None}

    def _extract(self, text: str) -> dict:
        items = []
        for line in re.findall(r"\[(R\d+)\] \((.*?)\) (.*)", text):
            rid, _loc, rest = line
            cells = {}
            for part in rest.split(" | "):
                if ": " in part:
                    k, v = part.split(": ", 1)
                    cells[k] = (v, part)
            g = lambda k: self._field(*cells[k]) if k in cells else self._field(None)  # noqa: E731
            berat = g("Berat")
            if self.hallucinate and berat["nilai"] is None:
                berat = {"nilai": "999 g", "kutipan": "Berat: 999 g"}      # tidak ada di sumber
            items.append({"lokasi": rid, "nama": g("Nama"), "merek": g("Merek"), "tipe": g("Tipe"), "spesifikasi": g("Spesifikasi"),
                          "kode_part": g("Kode"), "satuan": g("Satuan"), "berat": berat, "panjang": g("Panjang"), "lebar": g("Lebar"),
                          "tinggi": g("Tinggi"), "negara_asal": g("Negara"), "harga_beli": g("Harga Beli"), "stok": g("Stok"), "garansi": g("Garansi")})
        return {"items": items}

    def _classify(self, text: str) -> dict:
        m = re.search(r"Item:\n(\[.*?\])\n\nKandidat kategori", text, re.S)
        items = json.loads(m.group(1))
        table = {c["id"]: c for c in json.loads(text.split("Kandidat kategori (id, kategori, KBKI):\n", 1)[1])}
        out = []
        for it in items:
            cid = it["kandidat"][0]
            kb = table[cid]["kbki"][0]["kode"]
            alt = it["kandidat"][1:3]
            if self.bad_category:
                cid = "999999"
            if self.bad_kbki:
                kb = "0000000000"
            out.append({"item_id": it["item_id"], "kategori_id": cid, "alternatif": alt, "skor": 0.9, "kbki": kb, "alasan": "cocok dengan nama produk"})
        return {"hasil": out}
