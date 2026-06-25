"""Hierarquia de erros do toolkit.

Os adaptadores traduzem essas exceções em códigos de saída (CLI) ou status HTTP (API).
"""

from __future__ import annotations


class ImageToolkitError(Exception):
    """Raiz de todos os erros tratáveis do toolkit."""


class InvalidInputError(ImageToolkitError):
    """Entrada inválida: arquivo não é imagem, parâmetro fora de faixa, etc."""


class UnsupportedFormatError(InvalidInputError):
    """Formato de imagem solicitado não é suportado pelo motor atual."""


class OperationError(ImageToolkitError):
    """Falha durante a execução de uma operação (motor retornou erro)."""


class MissingDependencyError(ImageToolkitError):
    """Funcionalidade requer uma dependência/binário opcional não instalado."""
