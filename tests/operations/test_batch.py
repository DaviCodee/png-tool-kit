"""Testes da operação em lote ``batch-convert``."""

from __future__ import annotations

import pytest

from pngtoolkit.core.errors import InvalidInputError
from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def _run(name: str, datas: list[bytes], src_names: list[str], **params):
    op = get_operation(name)
    return op.execute(
        [ImageInput(d, n) for d, n in zip(datas, src_names, strict=True)],
        op.params_model(**params),
    )


def test_batch_convert_converts_each_input(png, jpg):
    result = _run(
        "batch-convert",
        [png, jpg],
        ["fotos/a.png", "fotos/sub/b.jpg"],
        format="webp",
    )
    assert len(result.artifacts) == 2
    assert result.artifacts[0].filename == "fotos/a.webp"
    assert result.artifacts[1].filename == "fotos/sub/b.webp"
    assert all(a.media_type == "image/webp" for a in result.artifacts)
    assert result.meta["count"] == 2
    assert result.meta["format"] == "webp"


def test_batch_convert_preserves_subpath(png):
    result = _run(
        "batch-convert", [png], ["a/b/c/d/foto.png"], format="png"
    )
    assert result.artifacts[0].filename == "a/b/c/d/foto.png"


def test_batch_convert_empty_inputs():
    result = _run("batch-convert", [], [], format="webp")
    assert result.artifacts == []
    assert result.meta["count"] == 0


def test_batch_convert_rejects_garbage(make_image):
    bogus = ImageInput(b"not an image", "ruim.png")
    op = get_operation("batch-convert")
    with pytest.raises(InvalidInputError):
        op.execute([bogus], op.params_model(format="webp"))


def test_batch_convert_delete_flag_in_meta(png):
    result = _run(
        "batch-convert", [png], ["a.png"], format="webp", delete_originals=True
    )
    assert result.meta["delete_originals"] is True
