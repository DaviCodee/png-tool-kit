"""Testes das operações de transformação geométrica."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from pngtoolkit.core.errors import InvalidInputError
from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def _run(name: str, datas: list[bytes], **params):
    op = get_operation(name)
    return op.execute([ImageInput(d) for d in datas], op.params_model(**params))


def _size(data: bytes) -> tuple[int, int]:
    return Image.open(BytesIO(data)).size


def test_resize_by_width_keeps_aspect(png):
    result = _run("resize", [png], width=128)
    assert _size(result.single.data) == (128, 96)


def test_resize_by_percent(png):
    result = _run("resize", [png], percent=50)
    assert _size(result.single.data) == (32, 24)


def test_resize_requires_a_dimension(png):
    with pytest.raises(ValueError):
        _run("resize", [png])


def test_crop_box(png):
    result = _run("crop", [png], box=(0, 0, 20, 10))
    assert _size(result.single.data) == (20, 10)


def test_crop_anchored_center(png):
    result = _run("crop", [png], width=20, height=20, anchor="center")
    assert _size(result.single.data) == (20, 20)


def test_crop_box_out_of_bounds(png):
    with pytest.raises(InvalidInputError):
        _run("crop", [png], box=(0, 0, 999, 999))


def test_rotate_expands_canvas(png):
    result = _run("rotate", [png], degrees=90)
    assert _size(result.single.data) == (48, 64)


def test_flip_preserves_size(png):
    result = _run("flip", [png], direction="vertical")
    assert _size(result.single.data) == (64, 48)


def test_invalid_input_rejected():
    with pytest.raises(InvalidInputError):
        _run("resize", [b"not an image"], width=10)
