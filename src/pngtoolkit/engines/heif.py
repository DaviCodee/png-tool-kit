"""Suporte opcional a HEIC/HEIF via ``pillow-heif`` (extra ``heif``).

Registrar o opener habilita tanto a leitura (fotos de iPhone) quanto a gravação
``format=HEIF``. A importação é preguiçosa: o erro só ocorre quando uma operação
pede ``heic``/``heif`` sem o extra instalado.
"""

from __future__ import annotations

from pngtoolkit.core.errors import MissingDependencyError

_registered = False


def ensure_available() -> None:
    """Garante que o codec HEIF está registrado ou levanta erro orientando o extra."""
    global _registered
    if _registered:
        return
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
    except ImportError as exc:
        raise MissingDependencyError(
            "suporte a HEIC/HEIF requer o extra 'heif' (pip install pngtoolkit[heif])"
        ) from exc
    _registered = True
