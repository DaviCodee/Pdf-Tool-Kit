"""Validação de entrada e saneamento de nomes de arquivo."""

from __future__ import annotations

import os
import re

from pdftoolkit.core.errors import InvalidInputError

_PDF_MAGIC = b"%PDF-"
_SCAN_WINDOW = 1024


def looks_like_pdf(data: bytes) -> bool:
    """Heurística por magic bytes: ``%PDF-`` deve aparecer no início do arquivo.

    Alguns PDFs trazem bytes de lixo antes do cabeçalho, então procuramos dentro de
    uma janela inicial em vez de exigir o prefixo exato.
    """
    return _PDF_MAGIC in data[:_SCAN_WINDOW]


def ensure_pdf(data: bytes, name: str | None = None) -> None:
    """Levanta :class:`InvalidInputError` se ``data`` não parecer um PDF."""
    if not data:
        raise InvalidInputError(f"arquivo vazio: {name or 'entrada'}")
    if not looks_like_pdf(data):
        raise InvalidInputError(f"não parece um PDF: {name or 'entrada'}")


def safe_filename(name: str, *, fallback: str = "documento.pdf") -> str:
    """Reduz ``name`` ao componente base e remove caracteres perigosos."""
    base = os.path.basename(name or "").strip()
    base = base.replace("\x00", "")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base or fallback


def with_suffix(name: str, suffix: str) -> str:
    """Insere ``suffix`` antes da extensão: ``doc.pdf`` + ``-out`` -> ``doc-out.pdf``."""
    safe = safe_filename(name)
    stem, dot, ext = safe.rpartition(".")
    if not dot:
        return f"{safe}{suffix}"
    return f"{stem}{suffix}.{ext}"
