"""Operações de transformação geométrica: resize, crop, rotate, flip."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from pydantic import Field, model_validator

from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import register
from pngtoolkit.core.validation import ensure_image, with_suffix
from pngtoolkit.engines import pillow_engine as pe

if TYPE_CHECKING:  # pragma: no cover
    from PIL.Image import Image


def _artifact(image: Image, item: ImageInput, suffix: str) -> Artifact:
    """Serializa preservando o formato de origem e nomeia com ``suffix``."""
    fmt = pe.default_format(image)
    data = pe.to_bytes(image, fmt)
    return Artifact(
        data=data,
        filename=with_suffix(item.name, suffix),
        media_type=pe.media_type(fmt),
    )


class ResizeParams(OperationParams):
    """Informe ``percent``, ou ``width`` e/ou ``height`` (mantém proporção)."""

    width: int | None = Field(default=None, gt=0, description="largura alvo em pixels")
    height: int | None = Field(default=None, gt=0, description="altura alvo em pixels")
    percent: float | None = Field(
        default=None, gt=0, description="escala em porcentagem (ex.: 50 = metade)"
    )

    @model_validator(mode="after")
    def _at_least_one(self) -> ResizeParams:
        if self.percent is None and self.width is None and self.height is None:
            raise ValueError("informe 'percent', 'width' e/ou 'height'")
        if self.percent is not None and (self.width is not None or self.height is not None):
            raise ValueError("use 'percent' OU 'width'/'height', não ambos")
        return self


@register
class ResizeOperation(ImageOperation[ResizeParams]):
    name = "resize"
    category = "transformar"
    summary = "Redimensiona por largura, altura ou porcentagem (mantém a proporção)."
    params_model = ResizeParams

    def run(self, inputs: Sequence[ImageInput], params: ResizeParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        width, height = pe.compute_size(
            image, width=params.width, height=params.height, percent=params.percent
        )
        resized = pe.resize(image, width, height)
        artifact = _artifact(resized, item, "-redimensionado")
        return OperationResult(artifacts=[artifact], meta={"width": width, "height": height})


class CropParams(OperationParams):
    """Recorte por âncora (``width``+``height``+``anchor``) ou caixa explícita."""

    width: int | None = Field(
        default=None, gt=0, description="largura da janela (modo ancorado)"
    )
    height: int | None = Field(
        default=None, gt=0, description="altura da janela (modo ancorado)"
    )
    anchor: Literal[
        "center", "top-left", "top-right", "bottom-left", "bottom-right"
    ] = Field(default="center", description="onde ancorar a janela width x height")
    box: tuple[int, int, int, int] | None = Field(
        default=None,
        description="caixa em pixels: LEFT TOP RIGHT BOTTOM (origem no topo-esquerdo)",
    )

    @model_validator(mode="after")
    def _mode(self) -> CropParams:
        has_box = self.box is not None
        has_dims = self.width is not None and self.height is not None
        if has_box == has_dims:
            raise ValueError("informe 'box' OU 'width'+'height', exclusivamente")
        return self


@register
class CropOperation(ImageOperation[CropParams]):
    name = "crop"
    category = "transformar"
    summary = "Recorta por caixa de pixels ou por dimensão ancorada (centro/cantos)."
    params_model = CropParams

    def run(self, inputs: Sequence[ImageInput], params: CropParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        if params.box is not None:
            cropped = pe.crop_box(image, params.box)
        else:
            assert params.width is not None and params.height is not None
            cropped = pe.crop_anchored(image, params.width, params.height, params.anchor)
        artifact = _artifact(cropped, item, "-recortado")
        return OperationResult(
            artifacts=[artifact], meta={"width": cropped.size[0], "height": cropped.size[1]}
        )


class RotateParams(OperationParams):
    """Ângulo anti-horário em graus; ``expand`` ajusta a tela ao novo tamanho."""

    degrees: float
    expand: bool = True


@register
class RotateOperation(ImageOperation[RotateParams]):
    name = "rotate"
    category = "transformar"
    summary = "Gira a imagem por um ângulo qualquer (90/180/270 ou custom)."
    params_model = RotateParams

    def run(self, inputs: Sequence[ImageInput], params: RotateParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        rotated = pe.rotate(image, params.degrees, expand=params.expand)
        artifact = _artifact(rotated, item, "-girado")
        return OperationResult(artifacts=[artifact], meta={"degrees": params.degrees})


class FlipParams(OperationParams):
    """Espelhamento horizontal ou vertical."""

    direction: Literal["horizontal", "vertical"] = "horizontal"


@register
class FlipOperation(ImageOperation[FlipParams]):
    name = "flip"
    category = "transformar"
    summary = "Espelha a imagem na horizontal ou na vertical."
    params_model = FlipParams

    def run(self, inputs: Sequence[ImageInput], params: FlipParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        flipped = pe.flip(image, params.direction)
        artifact = _artifact(flipped, item, "-espelhado")
        return OperationResult(artifacts=[artifact], meta={"direction": params.direction})
