"""Remoção de fundo por IA rodando o U²-Net direto no ONNX Runtime (extra ``bg``).

Diferente do ``rembg``, este backend depende apenas de ``onnxruntime`` + ``numpy``
(ambos instalam em Python 3.13/3.14), evitando a cadeia ``pymatting``/``numba``/
``llvmlite``. O modelo ``.onnx`` é baixado uma única vez e cacheado em disco.

A implementação do pré/pós-processamento U²-Net (resize 320×320, normalização
ImageNet, normalização min-max da saliência e uso como canal alfa) é o pipeline
padrão e bem documentado desse modelo; nenhum código de terceiros é copiado.
"""

from __future__ import annotations

import os
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

from pngtoolkit.core.errors import (
    InvalidInputError,
    MissingDependencyError,
    OperationError,
)

# Modelo -> (URL do .onnx, tamanho de entrada). u2net e u2netp compartilham o pipeline.
_MODELS: dict[str, tuple[str, tuple[int, int]]] = {
    "u2net": (
        "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx",
        (320, 320),
    ),
    "u2netp": (
        "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx",
        (320, 320),
    ),
}
_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)

_sessions: dict[str, Any] = {}


def available_models() -> list[str]:
    """Nomes de modelo suportados por este backend."""
    return sorted(_MODELS)


def _deps() -> tuple[Any, Any]:
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError as exc:
        raise MissingDependencyError(
            "o modo 'ai' do remove-bg requer o extra 'bg' "
            "(pip install pngtoolkit[bg])"
        ) from exc
    return np, ort


def _cache_dir() -> Path:
    base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    target = base / "pngtoolkit"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _model_path(model: str) -> Path:
    url, _ = _MODELS[model]
    dest = _cache_dir() / f"{model}.onnx"
    if not dest.exists():
        partial = dest.with_suffix(".onnx.part")
        try:
            urllib.request.urlretrieve(url, partial)  # noqa: S310 - URL fixa e confiável
        except Exception as exc:
            partial.unlink(missing_ok=True)
            raise OperationError(
                f"falha ao baixar o modelo {model!r} de {url}: {exc}"
            ) from exc
        partial.replace(dest)
    return dest


def _session(model: str, ort: Any) -> Any:
    if model not in _sessions:
        _sessions[model] = ort.InferenceSession(
            str(_model_path(model)), providers=["CPUExecutionProvider"]
        )
    return _sessions[model]


def remove_background(data: bytes, *, model: str = "u2net") -> bytes:
    """Remove o fundo via U²-Net e devolve um PNG RGBA com o objeto recortado."""
    if model not in _MODELS:
        raise InvalidInputError(
            f"modelo desconhecido: {model!r}; use um de {available_models()}"
        )
    np, ort = _deps()

    source = Image.open(BytesIO(data))
    source.load()
    _, size = _MODELS[model]

    rgb = source.convert("RGB").resize(size, Image.Resampling.LANCZOS)
    array = np.array(rgb).astype("float32")
    peak = array.max()
    if peak > 0:
        array = array / peak
    normalized = np.zeros_like(array)
    for channel in range(3):
        normalized[:, :, channel] = (array[:, :, channel] - _MEAN[channel]) / _STD[channel]
    tensor = normalized.transpose(2, 0, 1)[np.newaxis, :, :, :].astype("float32")

    session = _session(model, ort)
    input_name = session.get_inputs()[0].name
    prediction = session.run(None, {input_name: tensor})[0][0, 0, :, :]

    low, high = prediction.min(), prediction.max()
    if high > low:
        prediction = (prediction - low) / (high - low)
    mask_array = (prediction * 255).astype("uint8")
    mask = Image.fromarray(mask_array, mode="L").resize(
        source.size, Image.Resampling.LANCZOS
    )

    result = source.convert("RGBA")
    result.putalpha(mask)
    buffer = BytesIO()
    result.save(buffer, format="PNG")
    return buffer.getvalue()
