"""pdftoolkit — núcleo concentrador de operações de PDF.

Expõe um registro de operações consumido pelos adaptadores (CLI, API e GUI futura).
"""

from pdftoolkit.core.errors import (
    EncryptedPdfError,
    InvalidInputError,
    MissingDependencyError,
    OperationError,
    PageRangeError,
    PdfToolkitError,
)
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.registry import all_operations, get_operation, register

__version__ = "0.2.1"

__all__ = [
    "Artifact",
    "EncryptedPdfError",
    "InvalidInputError",
    "MissingDependencyError",
    "OperationError",
    "OperationResult",
    "PageRangeError",
    "PdfInput",
    "PdfOperation",
    "PdfToolkitError",
    "all_operations",
    "get_operation",
    "register",
]
