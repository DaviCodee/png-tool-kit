"""Remoção de fundo por IA via ``rembg`` (extra ``bg``).

Importação preguiçosa: o erro só ocorre quando o modo ``ai`` é usado sem o extra
instalado. O ``rembg`` baixa os pesos do modelo na primeira execução e os cacheia em
``~/.u2net``. Roda sobre ``onnxruntime`` (CPU por padrão).
"""

from __future__ import annotations

from typing import Any

from pngtoolkit.core.errors import MissingDependencyError, OperationError

_sessions: dict[str, Any] = {}


def _rembg() -> Any:
    try:
        import rembg
    except ImportError as exc:
        raise MissingDependencyError(
            "remoção de fundo por IA requer o extra 'bg' (pip install pngtoolkit[bg])"
        ) from exc
    return rembg


def _session(model: str) -> Any:
    rembg = _rembg()
    if model not in _sessions:
        _sessions[model] = rembg.new_session(model)
    return _sessions[model]


def remove_background(data: bytes, *, model: str = "u2net") -> bytes:
    """Remove o fundo e devolve um PNG RGBA. ``model`` é um modelo do rembg."""
    rembg = _rembg()
    try:
        result = rembg.remove(data, session=_session(model))
    except MissingDependencyError:
        raise
    except Exception as exc:  # pragma: no cover - falhas do modelo/onnxruntime
        raise OperationError(f"falha ao remover fundo: {exc}") from exc
    return bytes(result)
