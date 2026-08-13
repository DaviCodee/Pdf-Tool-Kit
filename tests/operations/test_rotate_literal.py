"""Testes do Literal[int] Rotation em rotate/batch-rotate."""

from __future__ import annotations

from io import BytesIO

import pytest
from pydantic import ValidationError
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation


def _text_pdf(text: str = "rotate me") -> bytes:
    buf = BytesIO()
    canvas = Canvas(buf)
    canvas.drawString(72, 720, text)
    canvas.showPage()
    canvas.save()
    return buf.getvalue()


def test_rotate_accepts_all_literal_degrees():
    """Rotation aceita os 6 valores: 90, -90, 180, -180, 270, -270."""
    op = get_operation("rotate")
    for d in (90, -90, 180, -180, 270, -270):
        params = op.params_model(degrees=d)
        assert params.degrees == d


def test_rotate_rejects_non_literal_degrees():
    """45, 91, 0, 360 → rejeitados (não são múltiplos de 90 válidos)."""
    op = get_operation("rotate")
    for bad in (45, 91, 0, 360, 30, "not-a-number"):
        with pytest.raises(ValidationError):
            op.params_model(degrees=bad)


def test_rotate_schema_enum_carries_values():
    """JSON Schema tem `enum: [90, -90, 180, -180, 270, -270]`."""
    op = get_operation("rotate")
    schema = op.params_model.model_json_schema()
    prop = schema["properties"]["degrees"]
    # Não-Optional[int] Literal → enum direto no topo.
    assert prop["enum"] == [90, -90, 180, -180, 270, -270]
    assert prop["type"] == "integer"


def test_batch_rotate_accepts_all_literal_degrees():
    """Batch-rotate segue o mesmo enum."""
    op = get_operation("batch-rotate")
    for d in (90, -90, 180, -180, 270, -270):
        params = op.params_model(degrees=d)
        assert params.degrees == d


def test_batch_rotate_schema_enum_carries_values():
    op = get_operation("batch-rotate")
    schema = op.params_model.model_json_schema()
    assert schema["properties"]["degrees"]["enum"] == [90, -90, 180, -180, 270, -270]


def test_rotate_runs_with_literal_degree():
    """Smoke: rotate aceita a config Literal e roda end-to-end."""
    op = get_operation("rotate")
    pdf = _text_pdf()
    result = op.execute([PdfInput(pdf, "in.pdf")], op.params_model(degrees=90))
    assert result.artifacts
    assert result.meta["pages"] == 1
