"""Testes da operação de redação (extra render)."""

from __future__ import annotations

from io import BytesIO

import pytest
from pydantic import ValidationError
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation

pytest.importorskip("fitz", reason="extra 'render' não instalado")


def _sensitive_pdf() -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(72, 720, "Nome: Joao Silva")
    canvas.drawString(72, 700, "CPF 123.456.789-00")
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _redact(data, **params):
    op = get_operation("redact")
    return op.execute([PdfInput(data)], op.params_model(**params))


def test_redact_terms():
    result = _redact(_sensitive_pdf(), terms=["Joao"])
    assert result.meta["redacted"] >= 1
    assert result.single.data[:4] == b"%PDF"


def test_redact_regex_cpf():
    result = _redact(_sensitive_pdf(), pattern=r"\d{3}\.\d{3}\.\d{3}-\d{2}")
    assert result.meta["redacted"] >= 1


def test_redact_requires_exactly_one():
    op = get_operation("redact")
    with pytest.raises(ValidationError):
        op.params_model()
    with pytest.raises(ValidationError):
        op.params_model(terms=["x"], pattern="y")
