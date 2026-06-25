"""Suporte opcional a AVIF via ``pillow-avif-plugin`` (extra ``avif``).

Importar o plugin registra o codec AVIF no Pillow. A importação é preguiçosa: o erro
só ocorre quando uma operação pede ``format=avif`` sem o extra instalado.
"""

from __future__ import annotations

from pngtoolkit.core.errors import MissingDependencyError

_registered = False


def ensure_available() -> None:
    """Garante que o codec AVIF está registrado ou levanta erro orientando o extra."""
    global _registered
    if _registered:
        return
    try:
        import pillow_avif  # noqa: F401  (efeito colateral: registra o codec)
    except ImportError as exc:
        raise MissingDependencyError(
            "suporte a AVIF requer o extra 'avif' (pip install pngtoolkit[avif])"
        ) from exc
    _registered = True
