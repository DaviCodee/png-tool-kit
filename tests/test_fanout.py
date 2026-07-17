"""Fan-out automático: operações 1/1 processando N entradas de uma vez."""

from __future__ import annotations

import pytest

from pngtoolkit.core.errors import ImageToolkitError
from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def test_fan_out_one_artifact_per_input(png, jpg):
    op = get_operation("compress")
    inputs = [
        ImageInput(png, "a.png"),
        ImageInput(jpg, "b.jpg"),
    ]
    result = op.execute(inputs, op.params_model())
    assert len(result.artifacts) == 2
    assert [a.filename for a in result.artifacts] == [
        "a-comprimido.png", "b-comprimido.jpg",
    ]
    assert result.meta["fan_out"] is True
    assert result.meta["inputs"] == 2
    assert [entry["name"] for entry in result.meta["per_input"]] == ["a.png", "b.jpg"]


def test_fan_out_preserves_relative_subpaths(png):
    op = get_operation("compress")
    inputs = [
        ImageInput(png, "fotos/a.png"),
        ImageInput(png, "outro/a.png"),
    ]
    result = op.execute(inputs, op.params_model())
    assert [a.filename for a in result.artifacts] == [
        "fotos/a-comprimido.png", "outro/a-comprimido.png",
    ]


def test_fan_out_dedupes_colliding_names(png):
    op = get_operation("compress")
    inputs = [ImageInput(png, "a.png"), ImageInput(png, "a.png")]
    result = op.execute(inputs, op.params_model())
    assert [a.filename for a in result.artifacts] == [
        "a-comprimido.png", "a-comprimido-2.png",
    ]


def test_fan_out_fails_fast_with_input_name(png):
    op = get_operation("compress")
    inputs = [
        ImageInput(png, "bom.png"),
        ImageInput(b"nao-e-imagem", "ruim.png"),
        ImageInput(png, "nunca.png"),
    ]
    with pytest.raises(ImageToolkitError) as excinfo:
        op.execute(inputs, op.params_model())
    assert str(excinfo.value).startswith("ruim.png: ")


def test_single_input_path_unchanged(png):
    op = get_operation("compress")
    result = op.execute([ImageInput(png, "a.png")], op.params_model())
    assert len(result.artifacts) == 1
    assert "fan_out" not in result.meta


def test_watermark_two_inputs_not_fanned_out(png):
    # watermark é 1/2 (base + logo opcional): 2 entradas usam o caminho normal
    # (logo como 2º input), não o fan-out.
    op = get_operation("watermark")
    result = op.execute(
        [ImageInput(png, "base.png"), ImageInput(png, "logo.png")],
        op.params_model(),
    )
    assert len(result.artifacts) == 1
    assert "fan_out" not in result.meta


def test_batch_convert_unbounded_op_not_fanned_out(png, jpg):
    op = get_operation("batch-convert")
    result = op.execute(
        [ImageInput(png, "a.png"), ImageInput(jpg, "b.jpg")],
        op.params_model(format="webp"),
    )
    # batch-convert já é 0/None e processa a lista inteira sozinho — o
    # fan-out genérico nunca deveria disparar (senão dobraria o processamento).
    assert len(result.artifacts) == 2
    assert "fan_out" not in result.meta
