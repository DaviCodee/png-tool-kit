"""Testes das operações de composição e efeitos."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from pngtoolkit.core.errors import InvalidInputError
from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def _run(name: str, datas: list[bytes], **params):
    op = get_operation(name)
    return op.execute([ImageInput(d, "foto.png") for d in datas], op.params_model(**params))


def test_watermark_text(png):
    result = _run("watermark", [png], text="© 2026")
    assert Image.open(BytesIO(result.single.data)).size == (64, 48)


def test_watermark_image(png, make_image):
    mark = make_image(16, 16)
    result = _run("watermark", [png, mark], position="top-left", opacity=0.7)
    assert result.single.filename == "foto-marca.png"


def test_watermark_without_text_or_mark_fails(png):
    with pytest.raises(InvalidInputError):
        _run("watermark", [png])


def test_blur_full(png):
    result = _run("blur", [png], radius=4)
    assert Image.open(BytesIO(result.single.data)).size == (64, 48)


def test_blur_region_out_of_bounds(png):
    with pytest.raises(InvalidInputError):
        _run("blur", [png], radius=4, region=(0, 0, 999, 999))


def test_favicon_emits_multiple_artifacts(png):
    result = _run("favicon", [png])
    names = {a.filename for a in result.artifacts}
    assert "favicon.ico" in names
    assert "favicon-16x16.png" in names
    assert any(a.media_type == "image/x-icon" for a in result.artifacts)
    ico = next(a for a in result.artifacts if a.filename == "favicon.ico")
    assert Image.open(BytesIO(ico.data)).format == "ICO"


def test_meme_requires_text(png):
    with pytest.raises(InvalidInputError):
        _run("meme", [png])


def test_meme_renders(png):
    result = _run("meme", [png], top="quando o teste", bottom="passa de primeira")
    assert Image.open(BytesIO(result.single.data)).size == (64, 48)
