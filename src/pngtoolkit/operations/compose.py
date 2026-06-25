"""Operações de composição e efeitos: watermark, blur, favicon, meme."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from pngtoolkit.core.errors import InvalidInputError
from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import register
from pngtoolkit.core.validation import ensure_image, replace_ext, with_suffix
from pngtoolkit.engines import pillow_engine as pe

_Position = Literal["top-left", "top-right", "bottom-left", "bottom-right", "center"]


class WatermarkParams(OperationParams):
    """Marca d'água de texto (``text``) ou de imagem (segundo arquivo de entrada)."""

    text: str | None = None
    position: _Position = "bottom-right"
    opacity: float = Field(default=0.5, ge=0.0, le=1.0)
    margin: int = Field(default=16, ge=0)
    font_size: int | None = Field(default=None, gt=0)


@register
class WatermarkOperation(ImageOperation[WatermarkParams]):
    name = "watermark"
    category = "composição"
    summary = "Aplica marca d'água de texto ou de imagem, com posição e opacidade."
    params_model = WatermarkParams
    min_inputs = 1
    max_inputs = 2

    def run(self, inputs: Sequence[ImageInput], params: WatermarkParams) -> OperationResult:
        base_item = inputs[0]
        ensure_image(base_item.data, base_item.name)
        base = pe.open_image(base_item.data, base_item.name)

        if len(inputs) == 2:
            mark_item = inputs[1]
            ensure_image(mark_item.data, mark_item.name)
            mark = pe.open_image(mark_item.data, mark_item.name)
            stamped = pe.stamp_image(
                base, mark, position=params.position,
                opacity=params.opacity, margin=params.margin,
            )
        elif params.text:
            stamped = pe.stamp_text(
                base, params.text, position=params.position, opacity=params.opacity,
                margin=params.margin, font_size=params.font_size,
            )
        else:
            raise InvalidInputError(
                "informe 'text' ou um segundo arquivo de imagem como marca d'água"
            )

        fmt = pe.default_format(base)
        data = pe.to_bytes(stamped, fmt)
        artifact = Artifact(
            data=data,
            filename=with_suffix(base_item.name, "-marca"),
            media_type=pe.media_type(fmt),
        )
        return OperationResult(artifacts=[artifact], meta={"position": params.position})


class BlurParams(OperationParams):
    """Desfoque gaussiano na imagem inteira ou só na ``region`` (caixa de pixels)."""

    radius: float = Field(default=8.0, gt=0)
    region: tuple[int, int, int, int] | None = None


@register
class BlurOperation(ImageOperation[BlurParams]):
    name = "blur"
    category = "composição"
    summary = "Aplica desfoque gaussiano total ou restrito a uma região."
    params_model = BlurParams

    def run(self, inputs: Sequence[ImageInput], params: BlurParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        if params.region is not None:
            left, top, right, bottom = params.region
            if not (0 <= left < right <= image.size[0] and 0 <= top < bottom <= image.size[1]):
                raise InvalidInputError("região de desfoque fora dos limites da imagem")
        blurred = pe.apply_blur(image, params.radius, params.region)
        fmt = pe.default_format(image)
        data = pe.to_bytes(blurred, fmt)
        artifact = Artifact(
            data=data,
            filename=with_suffix(item.name, "-desfoque"),
            media_type=pe.media_type(fmt),
        )
        return OperationResult(artifacts=[artifact], meta={"radius": params.radius})


class FaviconParams(OperationParams):
    """Sem parâmetros: gera o conjunto padrão de favicons."""


@register
class FaviconOperation(ImageOperation[FaviconParams]):
    name = "favicon"
    category = "composição"
    summary = "Gera favicons (16/32/180/192/512) e um favicon.ico multi-resolução."
    params_model = FaviconParams

    def run(self, inputs: Sequence[ImageInput], params: FaviconParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        outputs = pe.make_favicon(image)
        artifacts = [
            Artifact(data=data, filename=filename, media_type=media)
            for filename, data, media in outputs
        ]
        return OperationResult(artifacts=artifacts, meta={"files": len(artifacts)})


class MemeParams(OperationParams):
    """Texto do topo e/ou da base, em caixa-alta estilo impact."""

    top: str = ""
    bottom: str = ""


@register
class MemeOperation(ImageOperation[MemeParams]):
    name = "meme"
    category = "composição"
    summary = "Escreve texto no topo e na base estilo meme (branco com contorno)."
    params_model = MemeParams

    def run(self, inputs: Sequence[ImageInput], params: MemeParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        if not params.top and not params.bottom:
            raise InvalidInputError("informe 'top' e/ou 'bottom'")
        image = pe.open_image(item.data, item.name)
        meme = pe.make_meme(image, params.top, params.bottom)
        fmt = "jpg" if pe.default_format(image) == "jpg" else "png"
        data = pe.to_bytes(meme, fmt)
        artifact = Artifact(
            data=data,
            filename=replace_ext(item.name, fmt),
            media_type=pe.media_type(fmt),
        )
        return OperationResult(
            artifacts=[artifact], meta={"top": params.top, "bottom": params.bottom}
        )
