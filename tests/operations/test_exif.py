"""Testes das operações de metadados EXIF."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def _run(name: str, data: bytes):
    op = get_operation(name)
    return op.execute([ImageInput(data, "foto.jpg")], op.params_model())


def test_exif_read_returns_tags(jpg_with_exif):
    result = _run("exif-read", jpg_with_exif)
    assert result.artifacts == []
    assert result.meta["count"] >= 2
    assert result.meta["exif"]["Make"] == "PngToolKit"


def test_strip_exif_removes_tags(jpg_with_exif):
    result = _run("strip-exif", jpg_with_exif)
    cleaned = Image.open(BytesIO(result.single.data))
    assert len(cleaned.getexif()) == 0
