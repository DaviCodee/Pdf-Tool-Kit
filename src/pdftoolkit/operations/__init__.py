"""Operações do toolkit.

Importar este pacote registra todas as operações no registro central (efeito colateral
dos decoradores ``@register`` em cada módulo).
"""

from pdftoolkit.operations import (  # noqa: F401
    crop,
    merge,
    metadata,
    page_numbers,
    pages,
    rotate,
    security,
    split,
    watermark,
)
