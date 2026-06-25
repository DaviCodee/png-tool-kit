"""Validação de entrada e saneamento de nomes de arquivo."""

from __future__ import annotations

import os
import re

from pngtoolkit.core.errors import InvalidInputError

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_GIF_MAGICS = (b"GIF87a", b"GIF89a")
_BMP_MAGIC = b"BM"
_TIFF_MAGICS = (b"II*\x00", b"MM\x00*")
_RIFF_MAGIC = b"RIFF"
_WEBP_MAGIC = b"WEBP"


def looks_like_image(data: bytes) -> bool:
    """Heurística por magic bytes dos formatos suportados pelo Pillow.

    Cobre PNG, JPEG, GIF, BMP, TIFF e WebP. Não substitui a abertura real pelo
    motor, mas rejeita lixo cedo, antes de invocar o Pillow.
    """
    if data.startswith(_PNG_MAGIC):
        return True
    if data.startswith(_JPEG_MAGIC):
        return True
    if data.startswith(_GIF_MAGICS):
        return True
    if data.startswith(_BMP_MAGIC):
        return True
    if data.startswith(_TIFF_MAGICS):
        return True
    if data[:4] == _RIFF_MAGIC and data[8:12] == _WEBP_MAGIC:
        return True
    return False


def ensure_image(data: bytes, name: str | None = None) -> None:
    """Levanta :class:`InvalidInputError` se ``data`` não parecer uma imagem."""
    if not data:
        raise InvalidInputError(f"arquivo vazio: {name or 'entrada'}")
    if not looks_like_image(data):
        raise InvalidInputError(f"não parece uma imagem: {name or 'entrada'}")


def safe_filename(name: str, *, fallback: str = "imagem.png") -> str:
    """Reduz ``name`` ao componente base e remove caracteres perigosos."""
    base = os.path.basename(name or "").strip()
    base = base.replace("\x00", "")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base or fallback


def with_suffix(name: str, suffix: str) -> str:
    """Insere ``suffix`` antes da extensão: ``foto.png`` + ``-out`` -> ``foto-out.png``."""
    safe = safe_filename(name)
    stem, dot, ext = safe.rpartition(".")
    if not dot:
        return f"{safe}{suffix}"
    return f"{stem}{suffix}.{ext}"


def replace_ext(name: str, ext: str, *, fallback_stem: str = "imagem") -> str:
    """Troca a extensão de ``name`` por ``ext`` (sem ponto), saneando o nome."""
    safe = safe_filename(name)
    stem, dot, _ = safe.rpartition(".")
    base = stem if dot else safe
    base = base or fallback_stem
    return f"{base}.{ext}"
