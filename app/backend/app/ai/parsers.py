"""Parser dokumen supplier. Excel/CSV diparse dengan KODE lalu dikirim per potongan (bukan sebagai file);
PDF dikirim sebagai content part file; gambar di-resize ke <=1600px."""
import base64
import csv
import io
from pathlib import Path

from openpyxl import load_workbook
from PIL import Image, ImageOps

CHUNK = 25
MAX_ROWS = 2000
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def kind_of(filename: str) -> str | None:
    e = Path(filename).suffix.lower()
    if e in (".xlsx", ".xlsm"):
        return "xlsx"
    if e == ".csv":
        return "csv"
    if e == ".pdf":
        return "pdf"
    if e in IMAGE_EXT:
        return "image"
    return None


def _clean(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _rows_from_matrix(matrix: list, sheet: str) -> list:
    """matrix: list baris (list nilai). Baris pertama yang terisi = header."""
    out, header, hdr_idx = [], None, None
    for i, row in enumerate(matrix, 1):
        cells = [_clean(c) for c in row]
        if not any(cells):
            continue
        if header is None:
            header, hdr_idx = [c or f"Kolom{j + 1}" for j, c in enumerate(cells)], i
            continue
        pairs = [(h, c) for h, c in zip(header, cells) if c]
        if not pairs:
            continue
        loc = f"{sheet}!baris {i}" if sheet else f"baris {i}"
        out.append({"id": f"R{len(out) + 1}", "loc": loc, "cells": dict(pairs),
                    "text": " | ".join(f"{h}: {c}" for h, c in pairs)})
    return out


def parse_tabular(path: str, kind: str) -> list:
    rows: list = []
    if kind == "xlsx":
        wb = load_workbook(path, read_only=True, data_only=True)
        for ws in wb.worksheets:
            rows += _rows_from_matrix([list(r) for r in ws.iter_rows(values_only=True)], ws.title)
    else:
        raw = Path(path).read_bytes()
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        try:
            dialect = csv.Sniffer().sniff(text[:4000], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        rows = _rows_from_matrix(list(csv.reader(io.StringIO(text), dialect)), "")
    if len(rows) > MAX_ROWS:
        raise ValueError(f"Terlalu banyak baris ({len(rows)}). Batas {MAX_ROWS} baris per file; pecah file.")
    for n, r in enumerate(rows, 1):   # id unik lintas sheet
        r["id"] = f"R{n}"
    return rows


def chunk(rows: list, n: int = CHUNK) -> list:
    return [rows[i:i + n] for i in range(0, len(rows), n)]


def pdf_part(path: str, filename: str) -> dict:
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    return {"type": "file", "file": {"filename": filename, "file_data": f"data:application/pdf;base64,{b64}"}}


def pdf_plugins(ocr: bool) -> list:
    """Engine OCR untuk PDF hasil scan; PDF teks biasa memakai pemrosesan bawaan."""
    return [{"id": "file-parser", "pdf": {"engine": "mistral-ocr" if ocr else "pdf-text"}}]


def image_part(path: str, max_side: int = 1600) -> dict:
    img = ImageOps.exif_transpose(Image.open(path))
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=85)
    return {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}}
