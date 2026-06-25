"""Execução segura de processos externos.

Usado por operações que dependem de binários do sistema (ex.: magick, potrace). Nunca
usa shell, sempre lista de argumentos, com timeout e captura de stderr.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from pngtoolkit.core.errors import MissingDependencyError, OperationError

_DEFAULT_TIMEOUT = 120


def require_binary(name: str) -> str:
    """Retorna o caminho do binário ``name`` ou levanta :class:`MissingDependencyError`."""
    path = shutil.which(name)
    if path is None:
        raise MissingDependencyError(
            f"o binário {name!r} não está instalado ou não está no PATH"
        )
    return path


def run_command(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> subprocess.CompletedProcess[bytes]:
    """Executa ``args`` e levanta :class:`OperationError` em caso de falha."""
    try:
        completed = subprocess.run(  # noqa: S603 - args sempre é lista, sem shell
            list(args),
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise MissingDependencyError(f"executável não encontrado: {args[0]!r}") from exc
    except subprocess.TimeoutExpired as exc:
        raise OperationError(f"tempo esgotado ao executar {args[0]!r}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise OperationError(
            f"{args[0]!r} falhou (código {completed.returncode}): {detail[:500]}"
        )
    return completed
