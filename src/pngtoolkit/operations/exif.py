"""Operações de metadados EXIF: exif-read, strip-exif."""

from __future__ import annotations

from collections.abc import Sequence

from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.params import OperationParams
from pngtoolkit.core.registry import register
from pngtoolkit.core.validation import ensure_image, with_suffix
from pngtoolkit.engines import pillow_engine as pe


class ExifReadParams(OperationParams):
    """Sem parâmetros: lê os metadados EXIF."""


@register
class ExifReadOperation(ImageOperation[ExifReadParams]):
    name = "exif-read"
    category = "metadados"
    summary = "Lê os metadados EXIF e devolve como JSON (sem produzir arquivo)."
    params_model = ExifReadParams

    def run(self, inputs: Sequence[ImageInput], params: ExifReadParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        exif = pe.read_exif(image)
        return OperationResult(meta={"exif": exif, "count": len(exif)})


class StripExifParams(OperationParams):
    """Sem parâmetros: remove todos os metadados."""


@register
class StripExifOperation(ImageOperation[StripExifParams]):
    name = "strip-exif"
    category = "metadados"
    summary = "Remove EXIF e demais metadados (gps, modelo, data)."
    params_model = StripExifParams

    def run(self, inputs: Sequence[ImageInput], params: StripExifParams) -> OperationResult:
        item = inputs[0]
        ensure_image(item.data, item.name)
        image = pe.open_image(item.data, item.name)
        fmt = pe.default_format(image)
        clean = pe.strip_exif(image)
        data = pe.to_bytes(clean, fmt)
        artifact = Artifact(
            data=data,
            filename=with_suffix(item.name, "-sem-exif"),
            media_type=pe.media_type(fmt),
        )
        return OperationResult(artifacts=[artifact], meta={"stripped": True})
