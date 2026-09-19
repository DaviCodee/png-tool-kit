"""Operação em lote: converte todas as imagens de uma pasta, recursivamente."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath

from pydantic import Field

from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import register
from pngtoolkit.core.validation import ensure_image
from pngtoolkit.engines import ensure_codec
from pngtoolkit.engines import pillow_engine as pe
from pngtoolkit.engines.pillow_engine import OutputFormat


class BatchConvertParams(OperationParams):
    """Converte recursivamente.

    ``format`` é o destino (mesmos formatos do ``convert``); ``delete_originals`` é só
    um marcador — a exclusão física é responsabilidade do adaptador de I/O (CLI/API),
    que conhece os caminhos reais. A operação em si devolve os artefatos em memória.
    """

    format: OutputFormat = "webp"
    quality: int | None = Field(default=None, ge=1, le=100)
    delete_originals: bool = False


@register
class BatchConvertOperation(ImageOperation[BatchConvertParams]):
    name = "batch-convert"
    category = "formato"
    summary = "Converte todas as imagens em uma pasta, recursivamente."
    params_model = BatchConvertParams
    min_inputs = 0
    max_inputs = None

    def run(self, inputs: Sequence[ImageInput], params: BatchConvertParams) -> OperationResult:
        ensure_codec(params.format)
        artifacts: list[Artifact] = []
        for item in inputs:
            ensure_image(item.data, item.name)
            image = pe.open_image(item.data, item.name)
            data = pe.to_bytes(image, params.format, quality=params.quality)
            artifacts.append(
                Artifact(
                    data=data,
                    filename=str(PurePosixPath(item.name).with_suffix(f".{params.format}")),
                    media_type=pe.media_type(params.format),
                )
            )
        return OperationResult(
            artifacts=artifacts,
            meta={
                "count": len(artifacts),
                "format": params.format,
                "delete_originals": params.delete_originals,
            },
        )
