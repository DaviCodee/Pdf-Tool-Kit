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


# Limite de samples devolvidos no preview. Evita payload gigantes pra documentos
# com milhares de matches (cada sample é {page, term, text} ~100 chars).
_PREVIEW_SAMPLE_LIMIT = 25


def _preview_samples_for_terms(page: Any, terms: Sequence[str]) -> tuple[int, list[dict[str, Any]]]:
    """Itera `page.search_for(term)` pra cada termo, sem anotar/aplicar."""
    total = 0
    samples: list[dict[str, Any]] = []
    for term in terms:
        for rect in page.search_for(term):
            total += 1
            if len(samples) < _PREVIEW_SAMPLE_LIMIT:
                samples.append({
                    "term": term,
                    "text": page.get_text("text", clip=rect).strip()[:120],
                })
    return total, samples


def preview_terms(data: bytes, terms: Sequence[str]) -> dict[str, Any]:
    """Conta matches por termo sem aplicar redactions. Não altera o PDF."""
    fitz = _fitz()
    document = fitz.open(stream=data, filetype="pdf")
    try:
        total = 0
        samples: list[dict[str, Any]] = []
        for page_idx, page in enumerate(document, start=1):
            page_total, page_samples = _preview_samples_for_terms(page, terms)
            total += page_total
            for entry in page_samples:
                samples.append({"page": page_idx, **entry})
        return {"total": total, "samples": samples[:_PREVIEW_SAMPLE_LIMIT]}
    finally:
        document.close()


def preview_regex(data: bytes, pattern: str) -> dict[str, Any]:
    """Conta palavras que casam com a regex sem aplicar redactions."""
    fitz = _fitz()
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        raise OperationError(f"expressão regular inválida: {exc}") from exc
    document = fitz.open(stream=data, filetype="pdf")
    try:
        total = 0
        samples: list[dict[str, Any]] = []
        for page_idx, page in enumerate(document, start=1):
            for word in page.get_text("words"):
                if compiled.search(word[4]):
                    total += 1
                    if len(samples) < _PREVIEW_SAMPLE_LIMIT:
                        samples.append({
                            "page": page_idx,
                            "term": pattern,
                            "text": word[4][:120],
                        })
        return {"total": total, "samples": samples}
    finally:
        document.close()
