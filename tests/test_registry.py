"""Garante a consistência do concentrador: registro, schemas e adaptadores."""

from __future__ import annotations

from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import all_operations

EXPECTED = {
    "resize",
    "crop",
    "rotate",
    "flip",
    "convert",
    "compress",
    "grayscale",
    "exif-read",
    "strip-exif",
    "watermark",
    "blur",
    "favicon",
    "meme",
    "remove-bg",
    "png-to-svg",
}


def test_all_tier1_operations_registered():
    names = {op.name for op in all_operations()}
    assert EXPECTED <= names


def test_each_operation_is_well_formed():
    for op in all_operations():
        assert isinstance(op, ImageOperation)
        assert issubclass(op.params_model, OperationParams)
        assert op.category and op.summary
        # O schema JSON deve ser gerável (alimenta CLI, API e GUI).
        assert op.params_model.model_json_schema()["type"] == "object"
