"""Pemrosesan foto: EXIF, pad 1:1 latar putih (atau crop), resize 700x700, PNG < 1 MB. Banner jasa."""
import io

from PIL import Image, ImageDraw, ImageFont, ImageOps

MAX_BYTES = 1024 * 1024
TARGET = 700
MIN_SIDE, MAX_SIDE = 300, 2048


class PhotoError(ValueError):
    pass


def _png_bytes(img: Image.Image, quantize: bool = False) -> bytes:
    buf = io.BytesIO()
    im = img.quantize(colors=256, method=Image.Quantize.MEDIANCUT) if quantize else img
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def process_image(raw: bytes, crop: bool = False, size: int = TARGET) -> tuple:
    """Mengembalikan (png_bytes, width, height)."""
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:  # noqa: BLE001
        raise PhotoError(f"Bukan file gambar yang valid: {e}")
    img = ImageOps.exif_transpose(img)
    if min(img.size) < 100:
        raise PhotoError("Gambar terlalu kecil (minimal sisi terpendek 100 px).")
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        img = bg
    img = img.convert("RGB")
    size = max(MIN_SIDE, min(MAX_SIDE, size))
    if crop:
        img = ImageOps.fit(img, (size, size), Image.Resampling.LANCZOS)
    else:
        img.thumbnail((size, size), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (size, size), (255, 255, 255))
        canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
        img = canvas
    data = _png_bytes(img)
    s = size
    while len(data) >= MAX_BYTES and s > MIN_SIDE:   # turunkan resolusi
        s = max(MIN_SIDE, int(s * 0.85))
        data = _png_bytes(img.resize((s, s), Image.Resampling.LANCZOS))
    if len(data) >= MAX_BYTES:
        data = _png_bytes(img.resize((s, s), Image.Resampling.LANCZOS), quantize=True)  # kuantisasi
    if len(data) >= MAX_BYTES:
        raise PhotoError("Foto tidak bisa dikecilkan di bawah 1 MB.")
    out = Image.open(io.BytesIO(data))
    return data, out.width, out.height


def _font(size: int, bold=False):
    for name in (("arialbd.ttf" if bold else "arial.ttf"), ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_banner(title: str, points: list, company: str, size: int = TARGET) -> bytes:
    """Banner sederhana 1:1 untuk produk Jasa."""
    img = Image.new("RGB", (size, size), (30, 64, 175))
    d = ImageDraw.Draw(img)
    pad = int(size * 0.07)
    d.rectangle([0, int(size * 0.86), size, size], fill=(217, 119, 6))
    y = pad
    ft = _font(int(size * 0.075), True)
    for ln in _wrap(d, title, ft, size - 2 * pad)[:4]:
        d.text((pad, y), ln, font=ft, fill=(255, 255, 255))
        y += int(size * 0.09)
    y += int(size * 0.04)
    fp = _font(int(size * 0.045))
    for p in [x for x in points if x.strip()][:6]:
        for i, ln in enumerate(_wrap(d, p.strip(), fp, size - 2 * pad - 30)[:2]):
            if i == 0:
                d.ellipse([pad, y + 8, pad + 12, y + 20], fill=(251, 191, 36))
            d.text((pad + 28, y), ln, font=fp, fill=(255, 255, 255))
            y += int(size * 0.058)
        y += 6
    fc = _font(int(size * 0.04), True)
    d.text((pad, int(size * 0.885)), company[:50], font=fc, fill=(0, 0, 0))
    data = _png_bytes(img)
    if len(data) >= MAX_BYTES:
        data = _png_bytes(img, quantize=True)
    return data
