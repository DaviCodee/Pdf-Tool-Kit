"""Operações do toolkit.

Importar este pacote registra todas as operações no registro central (efeito colateral
dos decoradores ``@register`` em cada módulo).
"""

from pdftoolkit.operations import (  # noqa: F401
    compare,
    convert,
    crop,
    forms,
    merge,
    metadata,
    ocr,
    office,
    optimize,
    page_numbers,
    pages,
    redact,
    rotate,
    security,
    sign,
    split,
    tables,
    watermark,
)
