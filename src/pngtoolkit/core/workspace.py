"""Diretório de trabalho temporário com limpeza automática.

Usado por operações que precisam acionar processos externos (extra ``svg``). As
operações estruturais trabalham em memória e não precisam dele.
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree


@contextmanager
def temp_workspace(prefix: str = "pngtoolkit-") -> Iterator[Path]:
    """Cria um diretório temporário e o remove ao sair do contexto."""
    path = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)
