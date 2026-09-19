"""Testes das operações de formato e compressão."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image, features

from pngtoolkit.core.errors import MissingDependencyError
from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def _run(name: str, datas: list[bytes], *, src_name: str = "foto.png", **params):
    op = get_operation(name)
    return op.execute([ImageInput(d, src_name) for d in datas], op.params_model(**params))


def _save_image(image: Image.Image, fmt: str, **kwargs) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=fmt, **kwargs)
    return buffer.getvalue()


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


@pytest.mark.parametrize(
    ("fmt", "pillow_fmt", "media"),
    [
        ("tiff", "TIFF", "image/tiff"),
        ("tif", "TIFF", "image/tiff"),
        ("ico", "ICO", "image/x-icon"),
        ("jp2", "JPEG2000", "image/jp2"),
        ("tga", "TGA", "image/x-tga"),
        ("pcx", "PCX", "image/x-pcx"),
        ("ppm", "PPM", "image/x-portable-pixmap"),
        ("qoi", "QOI", "image/qoi"),
        ("sgi", "SGI", "image/x-sgi"),
        ("icns", "ICNS", "image/x-icns"),
        ("dds", "DDS", "image/x-dds"),
        ("xbm", "XBM", "image/x-xbitmap"),
        ("eps", "EPS", "application/postscript"),
    ],
)
def test_convert_to_new_formats(png, fmt, pillow_fmt, media):
    result = _run("convert", [png], format=fmt, src_name="foto.png")
    artifact = result.single
    assert artifact.filename == f"foto.{fmt}"
    assert artifact.media_type == media
    if fmt == "pdf":
        assert artifact.data.startswith(b"%PDF")
    else:
        assert Image.open(BytesIO(artifact.data)).format == pillow_fmt


def test_convert_to_avif(png):
    if not features.check("avif"):
        pytest.skip("Pillow sem AVIF nativo")
    result = _run("convert", [png], format="avif")
    artifact = result.single
    assert artifact.media_type == "image/avif"
    assert Image.open(BytesIO(artifact.data)).format == "AVIF"


def test_convert_from_avif_input():
    """Regressão: AVIF de entrada era rejeitado pelo looks_like_image."""
    if not features.check("avif"):
        pytest.skip("Pillow sem AVIF nativo")
    avif_bytes = _save_image(Image.new("RGB", (32, 32), (5, 6, 7)), "AVIF")
    result = _run("convert", [avif_bytes], format="png", src_name="conceito.avif")
    artifact = result.single
    assert artifact.filename == "conceito.png"
    assert Image.open(BytesIO(artifact.data)).format == "PNG"


def test_convert_from_tga_input():
    """Entrada sem assinatura (TGA) passa pelo fallback de decodificação."""
    tga_bytes = _save_image(Image.new("RGB", (16, 16), (9, 9, 9)), "TGA")
    result = _run("convert", [tga_bytes], format="webp", src_name="foto.tga")
    assert Image.open(BytesIO(result.single.data)).format == "WEBP"


def test_convert_from_ico_input():
    ico_bytes = _save_image(Image.new("RGBA", (32, 32), (1, 2, 3, 255)), "ICO")
    result = _run("convert", [ico_bytes], format="png", src_name="icone.ico")
    assert Image.open(BytesIO(result.single.data)).format == "PNG"


def test_convert_heic_requires_extra(png):
    """Sem pillow-heif, heic devolve MissingDependencyError (HTTP 501 na API)."""
    try:
        import pillow_heif  # noqa: F401
    except ImportError:
        with pytest.raises(MissingDependencyError):
            _run("convert", [png], format="heic")
        return
    pytest.skip("pillow-heif instalado — não dá pra testar o erro de dependência")


def test_convert_rgba_to_ppm_flattens_alpha():
    rgba = Image.new("RGBA", (16, 16), (10, 20, 30, 128))
    result = _run("convert", [_save_image(rgba, "PNG")], format="ppm")
    assert Image.open(BytesIO(result.single.data)).mode == "RGB"


def test_convert_rgba_to_qoi_keeps_alpha():
    rgba = Image.new("RGBA", (16, 16), (10, 20, 30, 128))
    result = _run("convert", [_save_image(rgba, "PNG")], format="qoi")
    assert Image.open(BytesIO(result.single.data)).mode == "RGBA"


def test_convert_grayscale_source_to_xbm_binarizes(make_image):
    result = _run("convert", [make_image()], format="xbm")
    assert Image.open(BytesIO(result.single.data)).mode == "1"


def test_compress_reports_sizes(jpg):
    result = _run("compress", [jpg], src_name="foto.jpg", quality=20)
    assert result.meta["result_bytes"] <= result.meta["original_bytes"]
    assert result.single.filename == "foto-comprimido.jpg"
    assert result.single.media_type == "image/jpeg"


def test_compress_jp2_source_resaves_as_jp2():
    jp2_bytes = _save_image(Image.new("RGB", (24, 24), (4, 5, 6)), "JPEG2000")
    result = _run("compress", [jp2_bytes], src_name="foto.jp2", quality=50)
    assert result.single.filename == "foto-comprimido.jp2"
    assert Image.open(BytesIO(result.single.data)).format == "JPEG2000"


def test_grayscale(png):
    result = _run("grayscale", [png])
    assert Image.open(BytesIO(result.single.data)).mode == "L"


def test_grayscale_tga_source_stays_tga():
    tga_bytes = _save_image(Image.new("RGB", (16, 16), (9, 9, 9)), "TGA")
    result = _run("grayscale", [tga_bytes], src_name="foto.tga")
    artifact = result.single
    assert artifact.filename == "foto-cinza.tga"
    assert Image.open(BytesIO(artifact.data)).mode == "L"

