"""Suporte a AVIF: nativo no Pillow 11.1+ (libavif) ou via ``pillow-avif-plugin``.

A checagem é preguiçosa: só roda quando uma operação pede o formato e o erro de
dependência aponta o extra correto para Pillow antigo.
"""

from __future__ import annotations

from pngtoolkit.core.errors import MissingDependencyError

_registered = False


def ensure_available() -> None:
    """Garante que o codec AVIF está registrado ou levanta erro orientando o extra."""
    global _registered
    if _registered:
        return
    from PIL import Image

    if "AVIF" in Image.OPEN and "AVIF" in Image.SAVE:
        _registered = True  # Pillow já vem com libavif embutido
        return
    try:
        import pillow_avif  # noqa: F401  (efeito colateral: registra o codec)
    except ImportError as exc:
        raise MissingDependencyError(
            "suporte a AVIF requer Pillow 11.1+ com libavif ou o extra 'avif' "
            "(pip install pngtoolkit[avif])"
        ) from exc
    _registered = True
