"""Operação de remoção de fundo: remove-bg (modos 'color' e 'ai')."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import register
from pngtoolkit.core.validation import ensure_image, replace_ext
from pngtoolkit.engines import onnx_bg
from pngtoolkit.engines import pillow_engine as pe


class RemoveBgParams(OperationParams):
    """Modo 'color' (rápido, fundo uniforme) ou 'ai' (retrato, requer extra 'bg')."""

    method: Literal["color", "ai"] = Field(
        default="color", description="'color' (rápido) ou 'ai' (rembg, requer extra bg)"
    )
    color: tuple[int, int, int] | None = Field(
        default=None, description="cor de fundo R G B (modo color; auto pelos cantos se omitido)"
    )
    tolerance: int = Field(
        default=30, ge=0, le=255, description="tolerância de cor 0–255 (modo color)"
    )
    model: Literal["u2net", "u2netp"] = Field(
        default="u2net", description="modelo U²-Net (modo ai): u2net (qualidade) ou u2netp (leve)"
    )


@register
class RemoveBgOperation(ImageOperation[RemoveBgParams]):
    name = "remove-bg"
    category = "composição"
    summary = "Remove o fundo por cor (rápido) ou por IA (retrato; extra 'bg')."
    params_model = RemoveBgParams

    def run(self, inputs: Sequence[ImageInput], params: RemoveBgParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        if params.method == "ai":
            data = onnx_bg.remove_background(item.data, model=params.model)
        else:
            image = pe.open_image(item.data, item.name)
            cut = pe.remove_background_color(
                image, color=params.color, tolerance=params.tolerance
            )
            data = pe.to_bytes(cut, "png")
        artifact = Artifact(
            data=data,
            filename=replace_ext(item.name, "png"),
            media_type="image/png",
        )
        return OperationResult(artifacts=[artifact], meta={"method": params.method})
