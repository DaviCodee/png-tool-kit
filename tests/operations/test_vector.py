"""Teste da operação de vetorização (extra svg: requer magick + potrace)."""

from __future__ import annotations

import shutil

import pytest

from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation

pytestmark = pytest.mark.skipif(
    shutil.which("magick") is None or shutil.which("potrace") is None,
    reason="binários 'magick'/'potrace' não disponíveis",
)


def test_png_to_svg(png):
    op = get_operation("png-to-svg")
    result = op.execute([ImageInput(png, "desenho.png")], op.params_model(threshold=50))
    artifact = result.single
    assert artifact.filename == "desenho.svg"
    assert artifact.media_type == "image/svg+xml"
    assert b"<svg" in artifact.data
