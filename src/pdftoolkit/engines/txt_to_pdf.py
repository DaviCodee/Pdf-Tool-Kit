"""Texto puro -> PDF via reportlab (já está nas dependências do núcleo).

Renderiza cada linha como um ``Paragraph`` em Helvetica, com quebra automática
quando necessário. Páginas em branco são inseridas quando o texto as contém.
"""

from __future__ import annotations

from io import BytesIO
from typing import Literal

from reportlab.lib.pagesizes import A4, LEGAL, LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

_PAGESIZES: dict[str, tuple[float, float]] = {
    "a4": A4,
    "letter": LETTER,
    "legal": LEGAL,
}


def txt_to_pdf(
    text: str,
    *,
    font_size: float = 11.0,
    page_size: Literal["a4", "letter", "legal"] = "a4",
) -> bytes:
    """Converte texto plano em PDF. Linhas vazias viram parágrafos em branco."""
    size = _PAGESIZES.get(page_size)
    if size is None:  # pragma: no cover - validado por Literal em OperationParams
        raise ValueError(f"page_size inválido: {page_size!r}")

    sample = getSampleStyleSheet()
    body = ParagraphStyle(
        "body",
        parent=sample["BodyText"],
        fontName="Helvetica",
        fontSize=float(font_size),
        leading=float(font_size) * 1.4,
    )

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=size,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="Texto convertido",
    )

    story = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            story.append(Spacer(1, body.leading))
            continue
        story.append(Paragraph(_xml_escape(raw_line), body))

    if not story:
        story.append(Paragraph("", body))

    document.build(story)
    return buffer.getvalue()


def _xml_escape(text: str) -> str:
    """Escapa caracteres especiais do reportlab (<, >, &)."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
