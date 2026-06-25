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
    """Verifica o contrato com o rembg sem depender da lib pesada (módulo fake)."""
    import sys
    import types

    calls: dict[str, object] = {}

    def new_session(model: str):
        calls["model"] = model
        return f"session:{model}"

    def remove(data: bytes, session=None):
        calls["session"] = session
        buffer = BytesIO()
        Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(buffer, format="PNG")
        return buffer.getvalue()

    fake = types.ModuleType("rembg")
    fake.new_session = new_session  # type: ignore[attr-defined]
    fake.remove = remove  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "rembg", fake)

    from pngtoolkit.engines import rembg_engine

    monkeypatch.setattr(rembg_engine, "_sessions", {})

    result = _run(_solid_with_square(), method="ai", model="u2net")
    assert calls["model"] == "u2net"
    assert calls["session"] == "session:u2net"
    out = Image.open(BytesIO(result.single.data))
    assert out.mode == "RGBA"
    assert result.single.media_type == "image/png"


def test_ai_mode_missing_dependency():
    """Garante a mensagem de erro orientando o extra quando rembg está ausente."""
    if importlib.util.find_spec("rembg") is not None:
        pytest.skip("rembg instalado")
    from pngtoolkit.core.errors import MissingDependencyError

    with pytest.raises(MissingDependencyError):
        _run(_solid_with_square(), method="ai")
