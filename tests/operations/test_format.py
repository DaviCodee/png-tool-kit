"""Testes das operações de formato e compressão."""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def _run(name: str, datas: list[bytes], *, src_name: str = "foto.png", **params):
    op = get_operation(name)
    return op.execute([ImageInput(d, src_name) for d in datas], op.params_model(**params))


def test_convert_to_webp(png):
    result = _run("convert", [png], format="webp")
    artifact = result.single
    assert artifact.filename.endswith(".webp")
    assert artifact.media_type == "image/webp"
    assert Image.open(BytesIO(artifact.data)).format == "WEBP"


def test_convert_to_jpg_drops_alpha(make_image):
    rgba = Image.new("RGBA", (20, 20), (10, 20, 30, 128))
    buffer = BytesIO()
    rgba.save(buffer, format="PNG")
    result = _run("convert", [buffer.getvalue()], format="jpg")
    assert Image.open(BytesIO(result.single.data)).mode == "RGB"


def test_compress_reports_sizes(jpg):
    result = _run("compress", [jpg], src_name="foto.jpg", quality=20)
    assert result.meta["result_bytes"] <= result.meta["original_bytes"]
    assert result.single.filename == "foto-comprimido.jpg"
    assert result.single.media_type == "image/jpeg"


def test_grayscale(png):
    result = _run("grayscale", [png])
    assert Image.open(BytesIO(result.single.data)).mode == "L"
