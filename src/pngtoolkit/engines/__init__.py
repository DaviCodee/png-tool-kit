"""Motores: invólucros finos sobre bibliotecas e binários externos."""

from __future__ import annotations

from pngtoolkit.engines import avif, heif

# Formatos de saída que dependem de codec registrado sob demanda.
_CODEC_FORMATS = {
    "avif": avif.ensure_available,
    "heic": heif.ensure_available,
    "heif": heif.ensure_available,
}


def ensure_codec(fmt: str) -> None:
    """Garante o codec do formato de saída quando ele não é nativo do Pillow."""
    ensure = _CODEC_FORMATS.get(fmt.lower())
    if ensure is not None:
        ensure()
