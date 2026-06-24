"""Redação real (remoção de conteúdo) via PyMuPDF (extra ``render``).

Diferente de só desenhar retângulos pretos, ``apply_redactions`` remove de fato o texto
e as imagens sob a área marcada.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from pdftoolkit.core.errors import MissingDependencyError, OperationError

_BLACK = (0.0, 0.0, 0.0)


def _fitz() -> Any:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise MissingDependencyError(
            "redação requer o extra 'render' (pip install pdftoolkit[render])"
        ) from exc
    return fitz


def redact_terms(data: bytes, terms: Sequence[str]) -> tuple[bytes, int]:
    """Remove todas as ocorrências dos termos informados (busca literal)."""
    fitz = _fitz()
    document = fitz.open(stream=data, filetype="pdf")
    try:
        marked = 0
        for page in document:
            for term in terms:
                for rect in page.search_for(term):
                    page.add_redact_annot(rect, fill=_BLACK)
                    marked += 1
            page.apply_redactions()
        return document.tobytes(), marked
    except Exception as exc:  # pragma: no cover
        raise OperationError(f"falha na redação: {exc}") from exc
    finally:
        document.close()


def redact_regex(data: bytes, pattern: str) -> tuple[bytes, int]:
    """Remove palavras cujo texto casa com a expressão regular."""
    fitz = _fitz()
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise OperationError(f"expressão regular inválida: {exc}") from exc
    document = fitz.open(stream=data, filetype="pdf")
    try:
        marked = 0
        for page in document:
            for word in page.get_text("words"):
                if compiled.search(word[4]):
                    page.add_redact_annot(fitz.Rect(word[:4]), fill=_BLACK)
                    marked += 1
            page.apply_redactions()
        return document.tobytes(), marked
    except Exception as exc:  # pragma: no cover
        raise OperationError(f"falha na redação: {exc}") from exc
    finally:
        document.close()
