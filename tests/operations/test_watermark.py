"""Testes da operação watermark."""

from __future__ import annotations

from io import BytesIO

import pytest
from pydantic import ValidationError
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.operations.watermark import WatermarkParams


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


def test_watermark_schema_has_opacity_help():
    """watermark.opacity carrega x-inputs.help descrevendo o range 0-1/0-100."""
    op = get_operation("watermark")
    schema = op.params_model.model_json_schema()
    x = schema.get("x-inputs", {})
    assert "opacity" in x
    assert "0-1" in x["opacity"]["help"] and "100" in x["opacity"]["help"]


# --- validator: aceita ratio 0-1 e percentual 1-100 ---

def test_opacity_ratio_0_15_kept():
    """0.15 (ratio) é aceito como 0.15 (sem conversão)."""
    p = WatermarkParams(text="x", opacity=0.15)
    assert p.opacity == 0.15


def test_opacity_percent_15_converted():
    """15 (percentual) é convertido para 0.15."""
    p = WatermarkParams(text="x", opacity=15)
    assert p.opacity == 0.15


def test_opacity_percent_50_converted():
    """50 → 0.5."""
    p = WatermarkParams(text="x", opacity=50)
    assert p.opacity == 0.5


def test_opacity_0_kept():
    """0 → 0.0 (invisível)."""
    p = WatermarkParams(text="x", opacity=0)
    assert p.opacity == 0.0


def test_opacity_100_converted_to_1():
    """100 (100%) → 1.0 (opaco total)."""
    p = WatermarkParams(text="x", opacity=100)
    assert p.opacity == 1.0


def test_opacity_string_15_converted():
    """String '15' (form-data) é convertido para 0.15."""
    p = WatermarkParams(text="x", opacity="15")
    assert p.opacity == 0.15


def test_opacity_string_0_5_kept():
    """String '0.5' (form-data) é mantida como 0.5."""
    p = WatermarkParams(text="x", opacity="0.5")
    assert p.opacity == 0.5


def test_opacity_above_100_rejected():
    """150 (>100) é rejeitado pelo ge=100.0."""
    with pytest.raises(ValidationError):
        WatermarkParams(text="x", opacity=150)


def test_opacity_negative_rejected():
    """-0.1 (<0) é rejeitado pelo ge=0.0."""
    with pytest.raises(ValidationError):
        WatermarkParams(text="x", opacity=-0.1)


def test_opacity_default_unchanged():
    """Default segue em 0.15 (mesmo de antes)."""
    p = WatermarkParams(text="x")
    assert p.opacity == 0.15


def test_opacity_schema_shows_max_100():
    """JSON Schema: maximum é 100 (não 1), pra documentar o range aceito."""
    op = get_operation("watermark")
    schema = op.params_model.model_json_schema()
    assert schema["properties"]["opacity"]["maximum"] == 100.0
    assert schema["properties"]["opacity"]["minimum"] == 0.0
    assert schema["properties"]["opacity"]["default"] == 0.15
