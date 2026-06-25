"""pngtoolkit — núcleo concentrador de operações de imagem.

Expõe um registro de operações consumido pelos adaptadores (CLI, API e GUI futura).
"""

from pngtoolkit.core.errors import (
    ImageToolkitError,
    InvalidInputError,
    MissingDependencyError,
    OperationError,
    UnsupportedFormatError,
)
from pngtoolkit.core.io import Artifact, ImageInput, OperationResult
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.registry import all_operations, get_operation, register

__version__ = "0.1.0"

__all__ = [
    "Artifact",
    "ImageInput",
    "ImageOperation",
    "ImageToolkitError",
    "InvalidInputError",
    "MissingDependencyError",
    "OperationError",
    "OperationResult",
    "UnsupportedFormatError",
    "all_operations",
    "get_operation",
    "register",
]
