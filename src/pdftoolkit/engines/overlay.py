"""Geração de páginas de carimbo (overlays) via reportlab.

Produz PDFs de uma página, do tamanho exato da página de destino, que depois são
compostos sobre/sob o conteúdo original pelo pypdf.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib.colors import Color
from reportlab.pdfgen.canvas import Canvas

# Âncoras horizontais suportadas para o texto.
Anchor = str  # "left" | "center" | "right"


def make_text_overlay(
    width: float,
    height: float,
    text: str,
    *,
    x: float,
    y: float,
    font: str = "Helvetica",
    size: float = 11.0,
    anchor: Anchor = "center",
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> bytes:
    """Cria um overlay de uma página com ``text`` numa posição absoluta."""
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=(width, height))
    canvas.setFont(font, size)
    canvas.setFillColor(Color(*rgb))
    if anchor == "left":
        canvas.drawString(x, y, text)
    elif anchor == "right":
        canvas.drawRightString(x, y, text)
    else:
        canvas.drawCentredString(x, y, text)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def make_watermark_overlay(
    width: float,
    height: float,
    text: str,
    *,
    font: str = "Helvetica-Bold",
    size: float = 48.0,
    opacity: float = 0.15,
    angle: float = 45.0,
    rgb: tuple[float, float, float] = (0.5, 0.5, 0.5),
) -> bytes:
    """Cria um overlay com uma marca d'água diagonal centralizada."""
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=(width, height))
    canvas.setFont(font, size)
    canvas.setFillColor(Color(*rgb))
    canvas.setFillAlpha(max(0.0, min(1.0, opacity)))
    canvas.saveState()
    canvas.translate(width / 2.0, height / 2.0)
    canvas.rotate(angle)
    canvas.drawCentredString(0.0, 0.0, text)
    canvas.restoreState()
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()
