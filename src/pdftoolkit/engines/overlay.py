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


def make_image_overlay(
    width: float,
    height: float,
    image_data: bytes,
    *,
    x: float,
    y: float,
    img_width: float | None = None,
    img_height: float | None = None,
) -> bytes:
    """Cria um overlay de uma página com uma imagem posicionada em (x, y)."""
    from io import BytesIO as _BytesIO

    from reportlab.lib.utils import ImageReader

    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=(width, height))
    img = ImageReader(_BytesIO(image_data))
    iw, ih = img.getSize()
    if img_width is not None and img_height is None:
        draw_w, draw_h = img_width, img_width * ih / max(iw, 1)
    elif img_height is not None and img_width is None:
        draw_w, draw_h = img_height * iw / max(ih, 1), img_height
    elif img_width is not None and img_height is not None:
        draw_w, draw_h = img_width, img_height
    else:
        draw_w, draw_h = float(iw), float(ih)
    canvas.drawImage(img, x, y, width=draw_w, height=draw_h, mask="auto")
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
