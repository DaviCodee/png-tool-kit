"""Validação de entrada e saneamento de nomes de arquivo."""

from __future__ import annotations

import os
import re

from pngtoolkit.core.errors import InvalidInputError

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_GIF_MAGICS = (b"GIF87a", b"GIF89a")
_BMP_MAGIC = b"BM"
_TIFF_MAGICS = (b"II*\x00", b"MM\x00*")
_RIFF_MAGIC = b"RIFF"
_WEBP_MAGIC = b"WEBP"

# ISO BMFF (caixa ``ftyp``): AVIF e a família HEIF/HEIC (iPhone).
_FTYP_MAGIC = b"ftyp"
_FTYP_BRANDS = frozenset({
    b"avif", b"avis", b"av01",
    b"heic", b"heix", b"hevc", b"hevx",
    b"heim", b"heis", b"hevm", b"hevs",
    b"mif1", b"msf1",
})
# Assinatura da caixa ``jP `` do JPEG 2000 (jp2/jpx) e codestream cru (.j2k).
_JPEG2000_MAGIC = b"\x00\x00\x00\x0cjP  \r\n\x87\n"
_J2K_CODESTREAM = b"\xff\x4f\xff\x51"
_ICO_CUR_MAGICS = (b"\x00\x00\x01\x00", b"\x00\x00\x02\x00")
_PSD_MAGIC = b"8BPS"
_DDS_MAGIC = b"DDS "
_QOI_MAGIC = b"qoif"
_ICNS_MAGIC = b"icns"
_SGI_MAGIC = b"\x01\xda"
_SUN_MAGIC = b"\x59\xa6\x6a\x95"
_GBR_MAGIC = b"GIMP"
_DCX_MAGIC = b"\xb1\x68\xde\x3a"
_XBM_MAGIC = b"#define"
_XPM_MAGIC = b"/* XPM */"
_EPS_MAGIC = b"%!PS"
_FITS_MAGIC = b"SIMPLE  ="
_PNM_KINDS = frozenset(b"1234567")
_PNM_WHITESPACE = frozenset(b" \t\r\n\x0b\x0c")


def looks_like_image(data: bytes) -> bool:
    """Heurística por magic bytes dos formatos com assinatura conhecida.

    Cobre PNG, JPEG, GIF, BMP, TIFF, WebP, AVIF/HEIC/HEIF, JPEG 2000, ICO/CUR,
    PSD, DDS, QOI, ICNS, PNM, XBM, XPM, SGI, SUN raster, GBR, DCX, EPS, FITS,
    FLI e PCX. Formatos sem assinatura confiável (ex.: TGA) ficam para a
    tentativa real de decodificação feita por :func:`ensure_image`.
    """
    if data.startswith(_PNG_MAGIC):
        return True
    if data.startswith(_JPEG_MAGIC):
        return True
    if data.startswith(_GIF_MAGICS):
        return True
    if data.startswith(_BMP_MAGIC):
        return True
    if data.startswith(_TIFF_MAGICS):
        return True
    if data[:4] == _RIFF_MAGIC and data[8:12] == _WEBP_MAGIC:
        return True
    if data[4:8] == _FTYP_MAGIC and data[8:12] in _FTYP_BRANDS:
        return True
    if data.startswith(_JPEG2000_MAGIC) or data.startswith(_J2K_CODESTREAM):
        return True
    if data.startswith(_ICO_CUR_MAGICS):
        return True
    if data.startswith(_PSD_MAGIC):
        return True
    if data.startswith(_DDS_MAGIC):
        return True
    if data.startswith(_QOI_MAGIC):
        return True
    if data.startswith(_ICNS_MAGIC):
        return True
    if data.startswith(_SGI_MAGIC):
        return True
    if data.startswith(_SUN_MAGIC):
        return True
    if data.startswith(_GBR_MAGIC):
        return True
    if data.startswith(_DCX_MAGIC):
        return True
    if data.startswith(_XBM_MAGIC):
        return True
    if data.startswith(_XPM_MAGIC):
        return True
    if data.startswith(_EPS_MAGIC):
        return True
    if data.startswith(_FITS_MAGIC):
        return True
    if (
        len(data) >= 2
        and data[0] == 0x50
        and data[1] in _PNM_KINDS
        and (len(data) == 2 or data[2] in _PNM_WHITESPACE)
    ):
        return True
    if data[4:6] in (b"\x11\xaf", b"\x12\xaf"):  # FLI/FLC
        return True
    if data[:1] == b"\x0a" and len(data) >= 3 and data[1] <= 5 and data[2] == 1:
        return True  # PCX
    return False


def ensure_image(data: bytes, name: str | None = None) -> None:
    """Levanta :class:`InvalidInputError` se ``data`` não parecer uma imagem.

    Magic bytes rejeitam lixo cedo, sem tocar no Pillow. Quando a assinatura é
    desconhecida, faz uma tentativa real de decodificação antes de rejeitar —
    é o que deixa passar formatos sem assinatura confiável (TGA e variantes
    exóticas que o Pillow abre).
    """
    if not data:
        raise InvalidInputError(f"arquivo vazio: {name or 'entrada'}")
    if looks_like_image(data):
        return
    from pngtoolkit.engines import pillow_engine  # import tardio evita ciclo

    try:
        pillow_engine.open_image(data, name)
    except InvalidInputError:
        raise InvalidInputError(f"não parece uma imagem: {name or 'entrada'}") from None


def safe_filename(name: str, *, fallback: str = "imagem.png") -> str:
    """Reduz ``name`` ao componente base e remove caracteres perigosos."""
    base = os.path.basename(name or "").strip()
    base = base.replace("\x00", "")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base or fallback


def with_suffix(name: str, suffix: str) -> str:
    """Insere ``suffix`` antes da extensão: ``foto.png`` + ``-out`` -> ``foto-out.png``."""
    safe = safe_filename(name)
    stem, dot, ext = safe.rpartition(".")
    if not dot:
        return f"{safe}{suffix}"
    return f"{stem}{suffix}.{ext}"


def replace_ext(name: str, ext: str, *, fallback_stem: str = "imagem") -> str:
    """Troca a extensão de ``name`` por ``ext`` (sem ponto), saneando o nome."""
    safe = safe_filename(name)
    stem, dot, _ = safe.rpartition(".")
    base = stem if dot else safe
    base = base or fallback_stem
    return f"{base}.{ext}"
