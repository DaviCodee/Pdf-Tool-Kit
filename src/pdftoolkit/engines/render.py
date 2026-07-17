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
    """Renderiza páginas para imagens. ``fmt`` em ``{"png", "jpg", "ppm"}``."""
    if fmt in {"jpg", "jpeg"}:
        output_format = "jpeg"
    elif fmt == "ppm":
        output_format = "ppm"
    else:
        output_format = "png"
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


def page_to_svg(
    data: bytes,
    indices: Sequence[int] | None = None,
    *,
    password: str | None = None,
) -> list[bytes]:
    """Exporta páginas como SVG (vetorial), uma por entrada."""
    document = _open(data, password)
    try:
        chosen = range(document.page_count) if indices is None else indices
        return [
            document[index].get_svg_image().encode("utf-8") for index in chosen
        ]
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


def compare_visual(
    data1: bytes,
    data2: bytes,
    *,
    dpi: int = 120,
) -> tuple[bytes, bool]:
    """Compara dois PDFs visualmente, página a página.

    Renderiza cada página, calcula a diferença de pixels e devolve um PDF em
    que cada página é a renderização do primeiro documento com a região
    divergente contornada em vermelho. Retorna ``(pdf_bytes, has_diff)``.

    Requer os extras ``render`` (PyMuPDF) e ``images`` (Pillow).
    """
    import io

    try:
        from PIL import Image, ImageChops, ImageDraw
    except ImportError as exc:
        raise MissingDependencyError(
            "comparação visual requer o extra 'images' (pip install pdftoolkit[images])"
        ) from exc

    fitz = _fitz()
    doc1 = _open(data1, None)
    doc2 = _open(data2, None)
    out = fitz.open()
    has_diff = False
    try:
        total = max(doc1.page_count, doc2.page_count)
        for i in range(total):
            p1 = doc1[i] if i < doc1.page_count else None
            p2 = doc2[i] if i < doc2.page_count else None
            ref = p1 or p2
            img1 = (
                Image.open(io.BytesIO(p1.get_pixmap(dpi=dpi).tobytes("png"))).convert("RGB")
                if p1 else None
            )
            img2 = (
                Image.open(io.BytesIO(p2.get_pixmap(dpi=dpi).tobytes("png"))).convert("RGB")
                if p2 else None
            )
            if img1 and img2:
                if img1.size != img2.size:
                    img2 = img2.resize(img1.size)
                bbox = ImageChops.difference(img1, img2).getbbox()
                composite = img1.copy()
                if bbox:
                    has_diff = True
                    ImageDraw.Draw(composite).rectangle(bbox, outline=(255, 0, 0), width=4)
            else:
                # página existe em só um dos documentos
                has_diff = True
                if img1 is not None:
                    composite = img1
                else:
                    assert img2 is not None
                    composite = img2

            assert ref is not None

            buf = io.BytesIO()
            composite.save(buf, format="PNG")
            page = out.new_page(width=ref.rect.width, height=ref.rect.height)
            page.insert_image(ref.rect, stream=buf.getvalue())
        return out.tobytes(), has_diff
    finally:
        out.close()
        doc1.close()
        doc2.close()
