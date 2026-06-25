"""Operações de formato e compressão: convert, compress, grayscale."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import register
from pngtoolkit.core.validation import ensure_image, replace_ext, with_suffix
from pngtoolkit.engines import avif
from pngtoolkit.engines import pillow_engine as pe


class ConvertParams(OperationParams):
    """Formato de saída. ``avif`` exige o extra ``avif`` instalado."""

    format: Literal["png", "jpg", "webp", "gif", "bmp", "avif"] = "png"
    quality: int | None = Field(default=None, ge=1, le=100)


@register
class ConvertOperation(ImageOperation[ConvertParams]):
    name = "convert"
    category = "formato"
    summary = "Converte entre png, jpg, webp, gif, bmp e avif."
    params_model = ConvertParams

    def run(self, inputs: Sequence[ImageInput], params: ConvertParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        if params.format == "avif":
            avif.ensure_available()
        image = pe.open_image(item.data, item.name)
        data = pe.to_bytes(image, params.format, quality=params.quality)
        artifact = Artifact(
            data=data,
            filename=replace_ext(item.name, params.format),
            media_type=pe.media_type(params.format),
        )
        return OperationResult(artifacts=[artifact], meta={"format": params.format})


class CompressParams(OperationParams):
    """Recomprime preservando o formato. ``quality`` afeta jpg/webp/avif."""

    quality: int = Field(default=75, ge=1, le=100)
    optimize: bool = True


@register
class CompressOperation(ImageOperation[CompressParams]):
    name = "compress"
    category = "formato"
    summary = "Recomprime a imagem reduzindo o tamanho (quality + optimize)."
    params_model = CompressParams

    def run(self, inputs: Sequence[ImageInput], params: CompressParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        fmt = pe.default_format(image)
        if fmt == "avif":
            avif.ensure_available()
        data = pe.to_bytes(image, fmt, quality=params.quality, optimize=params.optimize)
        artifact = Artifact(
            data=data,
            filename=with_suffix(item.name, "-comprimido"),
            media_type=pe.media_type(fmt),
        )
        return OperationResult(
            artifacts=[artifact],
            meta={"original_bytes": len(item.data), "result_bytes": len(data)},
        )


class GrayscaleParams(OperationParams):
    """Sem parâmetros: converte para tons de cinza."""


@register
class GrayscaleOperation(ImageOperation[GrayscaleParams]):
    name = "grayscale"
    category = "formato"
    summary = "Converte a imagem para tons de cinza."
    params_model = GrayscaleParams

    def run(self, inputs: Sequence[ImageInput], params: GrayscaleParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        fmt = pe.default_format(image)
        gray = pe.to_grayscale(image)
        data = pe.to_bytes(gray, fmt)
        artifact = Artifact(
            data=data,
            filename=with_suffix(item.name, "-cinza"),
            media_type=pe.media_type(fmt),
        )
        return OperationResult(artifacts=[artifact], meta={"mode": "L"})
