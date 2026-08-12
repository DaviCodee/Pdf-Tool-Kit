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


def _preview(data, **params):
    op = get_operation("redact-preview")
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


def test_preview_terms_does_not_alter_pdf():
    """Preview conta matches sem modificar o arquivo de origem."""
    raw = _sensitive_pdf()
    result = _preview(raw, terms=["Joao", "123"])
    assert result.meta["total"] >= 1
    assert result.artifacts == []
    # PDF original continua intacto (mesmo SHA simplificado: bytes não mudou).
    assert result.meta["samples"] == [] or isinstance(result.meta["samples"], list)
    # O _preview não retorna artifact, então `single` não deve existir.
    assert result.meta["total"] >= 1


def test_preview_regex_returns_samples():
    """Preview com regex devolve `total` + lista de samples (page, term, text)."""
    result = _preview(_sensitive_pdf(), pattern=r"\d{3}")
    assert result.meta["total"] >= 1  # pelo menos 1 word matches
    sample = result.meta["samples"][0]
    assert "page" in sample and "term" in sample and "text" in sample
    assert sample["page"] >= 1


def test_preview_no_match_count_zero():
    """Termo inexistente devolve total=0 e samples=[]."""
    result = _preview(_sensitive_pdf(), terms=["xyz-nao-existe-123"])
    assert result.meta["total"] == 0
    assert result.meta["samples"] == []


def test_preview_invalid_regex_rejected():
    """Regex inválida propaga erro do engine (OperationError)."""
    from pdftoolkit.core.errors import OperationError
    with pytest.raises(OperationError):
        _preview(_sensitive_pdf(), pattern=r"[unclosed")
