"""Testes da validação de entrada (magic bytes + fallback de decodificação)."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image, features

from pngtoolkit.core.errors import InvalidInputError
from pngtoolkit.core.validation import ensure_image, looks_like_image


def _encoded(fmt: str, *, mode: str = "RGB") -> bytes:
    if mode == "RGBA":
        image = Image.new("RGBA", (8, 8), (1, 2, 3, 255))
    else:
        image = Image.new(mode, (8, 8), 120 if mode in ("L", "1") else (1, 2, 3))
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("data", "label"),
    [
        (_encoded("PNG"), "png"),
        (_encoded("JPEG"), "jpeg"),
        (_encoded("GIF"), "gif"),
        (_encoded("BMP"), "bmp"),
        (_encoded("TIFF"), "tiff"),
        (_encoded("WEBP"), "webp"),
        (b"\x00\x00\x00\x20ftypavif\x00\x00\x00\x00" + b"\x00" * 24, "avif"),
        (b"\x00\x00\x00\x20ftypheic\x00\x00\x00\x00" + b"\x00" * 24, "heic"),
        (b"\x00\x00\x00\x20ftypmif1\x00\x00\x00\x00" + b"\x00" * 24, "heif-mif1"),
        (_encoded("JPEG2000"), "jp2"),
        (b"\x00\x00\x01\x00" + b"\x00" * 27, "ico"),
        (b"\x00\x00\x02\x00" + b"\x00" * 27, "cur"),
        (b"8BPS" + b"\x00" * 30, "psd"),
        (b"DDS " + b"\x00" * 30, "dds"),
        (b"qoif" + b"\x00" * 30, "qoi"),
        (b"icns" + b"\x00" * 30, "icns"),
        (b"P6\n8 8\n255\n" + b"\x00" * 192, "ppm"),
        (b"P1\n1 1\n0\n", "pbm"),
        (b"#define im_width 8\n", "xbm"),
        (b"/* XPM */\n", "xpm"),
        (b"\x01\xda\x00\x01" + b"\x00" * 30, "sgi"),
        (b"\x59\xa6\x6a\x95" + b"\x00" * 30, "sun"),
        (b"%!PS-Adobe-3.0 EPSF-3.0\n", "eps"),
        (b"\x0a\x02\x01\x01\x08\x00", "pcx"),
    ],
)
def test_looks_like_image_accepts_known_magics(data: bytes, label: str) -> None:
    assert looks_like_image(data), label


def test_looks_like_image_accepts_real_avif() -> None:
    if not features.check("avif"):
        pytest.skip("Pillow sem AVIF nativo")
    assert looks_like_image(_encoded("AVIF"))


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"nao e uma imagem, so texto comum",
        b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00",  # mp4 (brand fora da lista)
    ],
)
def test_looks_like_image_rejects_garbage(data: bytes) -> None:
    assert not looks_like_image(data)


def test_ensure_image_accepts_tga() -> None:
    """TGA (assinatura que colide com ICO/CUR) é aceito e decodifica de verdade."""
    data = _encoded("TGA", mode="RGBA")
    ensure_image(data, "conceito.tga")


def test_ensure_image_rejects_garbage() -> None:
    with pytest.raises(InvalidInputError, match="não parece uma imagem"):
        ensure_image(b"definitivamente nao e imagem", "lixo.txt")
    with pytest.raises(InvalidInputError, match="arquivo vazio"):
        ensure_image(b"", "vazio.png")


def test_ensure_image_message_includes_name() -> None:
    with pytest.raises(InvalidInputError, match="arquivo vazio: conceito.avif"):
        ensure_image(b"", "conceito.avif")
