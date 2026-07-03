"""Operações do toolkit.

Importar este pacote registra todas as operações no registro central (efeito colateral
dos decoradores ``@register`` em cada módulo).
"""

from pdftoolkit.operations import (  # noqa: F401
    attachments,
    bookmarks,
    compare,
    convert,
    crop,
    extract,
    forms,
    inspect,
    layout,
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
