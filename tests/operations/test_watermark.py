"""Testes da operação watermark."""

from __future__ import annotations

from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation


def _text_pdf(text: str = "watermark me") -> bytes:
    buf = BytesIO()
    canvas = Canvas(buf)
    canvas.drawString(72, 720, text)
    canvas.showPage()
    canvas.save()
    return buf.getvalue()


def test_watermark_runs_with_defaults():
    op = get_operation("watermark")
    pdf = _text_pdf()
    result = op.execute([PdfInput(pdf, "in.pdf")], op.params_model(text="CONFIDENTIAL"))
    assert result.artifacts


def test_watermark_schema_has_opacity_presets():
    """watermark.opacity vem com x-inputs.number_with_presets pro hub."""
    op = get_operation("watermark")
    schema = op.params_model.model_json_schema()
    x = schema.get("x-inputs", {})
    assert "opacity" in x
    assert x["opacity"]["type"] == "number_with_presets"
    assert x["opacity"]["presets"] == [0.15, 0.3, 0.5, 0.7]
