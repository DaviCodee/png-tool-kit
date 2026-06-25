"""Testes da operação remove-bg (modo color sempre; modo ai se rembg presente)."""

from __future__ import annotations

import importlib.util
from io import BytesIO

import pytest
from PIL import Image

from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.registry import get_operation


def _run(data: bytes, **params):
    op = get_operation("remove-bg")
    return op.execute([ImageInput(data, "foto.png")], op.params_model(**params))


def _solid_with_square() -> bytes:
    """Fundo branco com um quadrado vermelho central."""
    image = Image.new("RGB", (40, 40), (255, 255, 255))
    for x in range(12, 28):
        for y in range(12, 28):
            image.putpixel((x, y), (200, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_color_mode_makes_background_transparent():
    result = _run(_solid_with_square(), method="color", tolerance=30)
    out = Image.open(BytesIO(result.single.data))
    assert out.mode == "RGBA"
    assert result.single.filename == "foto.png"
    assert result.single.media_type == "image/png"
    # Canto (fundo) transparente; centro (objeto) opaco.
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((20, 20))[3] == 255


def test_color_mode_explicit_color():
    result = _run(_solid_with_square(), method="color", color=(255, 255, 255), tolerance=10)
    out = Image.open(BytesIO(result.single.data))
    assert out.getpixel((0, 0))[3] == 0


def test_ai_mode_wiring(monkeypatch):
    """Verifica o pipeline U²-Net sem baixar o modelo nem depender do onnxruntime real.

    Injeta um ``onnxruntime`` fake (sessão que devolve uma saliência sintética) e
    evita o download. Usa numpy real (do extra dev) para exercitar pré/pós-processo.
    """
    np = pytest.importorskip("numpy")
    import sys
    import types

    calls: dict[str, object] = {}

    class FakeInput:
        name = "input"

    class FakeSession:
        def __init__(self, path, providers=None):
            calls["path"] = path
            calls["providers"] = providers

        def get_inputs(self):
            return [FakeInput()]

        def run(self, _outputs, feed):
            calls["feed_shape"] = next(iter(feed.values())).shape
            # Saliência alta no centro (objeto), baixa nas bordas (fundo).
            out = np.zeros((1, 1, 320, 320), dtype="float32")
            out[0, 0, 80:240, 80:240] = 1.0
            return [out]

    fake_ort = types.ModuleType("onnxruntime")
    fake_ort.InferenceSession = FakeSession  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)

    from pngtoolkit.engines import onnx_bg

    monkeypatch.setattr(onnx_bg, "_sessions", {})
    monkeypatch.setattr(onnx_bg, "_model_path", lambda model: "fake.onnx")

    result = _run(_solid_with_square(), method="ai", model="u2net")
    assert calls["path"] == "fake.onnx"
    assert calls["feed_shape"] == (1, 3, 320, 320)
    out = Image.open(BytesIO(result.single.data))
    assert out.mode == "RGBA"
    assert result.single.media_type == "image/png"
    # Centro opaco (objeto), canto transparente (fundo).
    assert out.getpixel((20, 20))[3] > out.getpixel((0, 0))[3]


def test_ai_mode_missing_dependency():
    """Sem o onnxruntime, o modo ai falha com MissingDependencyError (HTTP 501)."""
    if importlib.util.find_spec("onnxruntime") is not None:
        pytest.skip("onnxruntime instalado")
    from pngtoolkit.core.errors import MissingDependencyError

    with pytest.raises(MissingDependencyError):
        _run(_solid_with_square(), method="ai")
