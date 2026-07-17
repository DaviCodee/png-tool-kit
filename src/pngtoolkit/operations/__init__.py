"""Operações do toolkit.

Importar este pacote registra todas as operações no registro central (efeito colateral
dos decoradores ``@register`` em cada módulo).
"""

from pngtoolkit.operations import (  # noqa: F401
    background,
    batch,
    compose,
    exif,
    format,
    transform,
    vector,
)
