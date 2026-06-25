"""Rasterização de páginas via PyMuPDF (extra ``render``, AGPL).

Importação preguiçosa: o módulo carrega sem o PyMuPDF instalado; o erro só ocorre ao
usar uma função, com mensagem orientando a instalar o extra.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pdftoolkit.core.errors import EncryptedPdfError, MissingDependencyError, OperationError


def _fitz() -> Any:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise MissingDependencyError(
            "rasterização requer o extra 'render' (pip install pdftoolkit[render])"
        ) from exc
    return fitz


def _open(data: bytes, password: str | None) -> Any:
    fitz = _fitz()
    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:  # pragma: no cover - entrada corrompida
        raise OperationError(f"não foi possível abrir o PDF: {exc}") from exc
    if document.needs_pass and not document.authenticate(password or ""):
        raise EncryptedPdfError("PDF protegido: senha ausente ou incorreta")
    return document


def render_pages(
    data: bytes,
    indices: Sequence[int] | None = None,
    *,
    dpi: int = 150,
    fmt: str = "png",
    password: str | None = None,
) -> list[bytes]:
    """Renderiza páginas para imagens. ``fmt`` em ``{"png", "jpg"}``."""
    output_format = "jpeg" if fmt in {"jpg", "jpeg"} else "png"
    document = _open(data, password)
    try:
        chosen = range(document.page_count) if indices is None else indices
        images: list[bytes] = []
        for index in chosen:
            pixmap = document[index].get_pixmap(dpi=dpi)
            images.append(pixmap.tobytes(output_format))
        return images
    finally:
        document.close()


def thumbnails(
    data: bytes,
    indices: Sequence[int] | None = None,
    *,
    width: int = 256,
    password: str | None = None,
) -> list[bytes]:
    """Gera miniaturas PNG escaladas para ``width`` pixels de largura."""
    fitz = _fitz()
    document = _open(data, password)
    try:
        chosen = range(document.page_count) if indices is None else indices
        images: list[bytes] = []
        for index in chosen:
            page = document[index]
            zoom = width / float(page.rect.width or width)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            images.append(pixmap.tobytes("png"))
        return images
    finally:
        document.close()


def page_count(data: bytes, password: str | None = None) -> int:
    document = _open(data, password)
    try:
        return int(document.page_count)
    finally:
        document.close()


def detect_blank_pages(
    data: bytes,
    *,
    dpi: int = 72,
    threshold: float = 0.99,
    password: str | None = None,
) -> list[int]:
    """Retorna os índices (0-based) das páginas consideradas em branco.

    Uma página é em branco quando a proporção de pixels claros (>250 em escala de
    cinza) é maior ou igual a ``threshold``.
    """
    fitz = _fitz()
    document = _open(data, password)
    blank: list[int] = []
    try:
        for i in range(document.page_count):
            pixmap = document[i].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
            samples = pixmap.samples
            white = sum(1 for b in samples if b > 250)
            if white / max(len(samples), 1) >= threshold:
                blank.append(i)
    finally:
        document.close()
    return blank
