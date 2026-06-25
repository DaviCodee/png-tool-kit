"""Operação de vetorização: png-to-svg (extra ``svg``)."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import register
from pngtoolkit.core.validation import ensure_image, replace_ext
from pngtoolkit.engines import trace


class PngToSvgParams(OperationParams):
    """Limiar de binarização (1–99%) antes do traçado vetorial."""

    threshold: int = Field(default=50, ge=1, le=99)


@register
class PngToSvgOperation(ImageOperation[PngToSvgParams]):
    name = "png-to-svg"
    category = "vetor"
    summary = "Vetoriza a imagem para SVG (requer 'magick' e 'potrace' no sistema)."
    params_model = PngToSvgParams

    def run(self, inputs: Sequence[ImageInput], params: PngToSvgParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        svg = trace.png_to_svg(item.data, threshold=params.threshold)
        artifact = Artifact(
            data=svg,
            filename=replace_ext(item.name, "svg"),
            media_type="image/svg+xml",
        )
        return OperationResult(artifacts=[artifact], meta={"threshold": params.threshold})
