"""Fixtures compartilhadas: imagens geradas em runtime (nada binário é commitado)."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO

import pytest
from PIL import Image


def _make_image(
    width: int = 64,
    height: int = 48,
    color: tuple[int, int, int] = (200, 120, 40),
    fmt: str = "PNG",
) -> bytes:
    image = Image.new("RGB", (width, height), color)
    # Um retângulo de contraste ajuda traçado/threshold a produzir algo não trivial.
    for x in range(width // 4, width // 2):
        for y in range(height // 4, height // 2):
            image.putpixel((x, y), (10, 10, 10))
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def make_image() -> Callable[..., bytes]:
    return _make_image


@pytest.fixture
def png() -> bytes:
    return _make_image(64, 48, fmt="PNG")


@pytest.fixture
def jpg() -> bytes:
    return _make_image(64, 48, fmt="JPEG")


@pytest.fixture
def jpg_with_exif() -> bytes:
    image = Image.new("RGB", (40, 40), (50, 90, 160))
    exif = image.getexif()
    exif[0x010F] = "PngToolKit"  # Make
    exif[0x0110] = "Modelo Teste"  # Model
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()
