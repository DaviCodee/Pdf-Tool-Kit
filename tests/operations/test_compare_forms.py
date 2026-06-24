"""Testes de comparação e formulários (operações base, sem extras)."""

from __future__ import annotations

from io import BytesIO

from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation


def _text_pdf(line: str) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(72, 720, line)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _form_pdf() -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.acroForm.textfield(name="nome", x=120, y=715, width=200, height=18, borderWidth=1)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def test_compare_detects_changes():
    op = get_operation("compare")
    result = op.execute(
        [PdfInput(_text_pdf("alpha")), PdfInput(_text_pdf("beta"))], op.params_model()
    )
    assert result.meta["identical"] is False
    assert result.meta["added"] >= 1 and result.meta["removed"] >= 1


def test_compare_identical():
    op = get_operation("compare")
    same = _text_pdf("igual")
    result = op.execute([PdfInput(same), PdfInput(same)], op.params_model())
    assert result.meta["identical"] is True


def test_form_read_and_fill_roundtrip():
    form = _form_pdf()
    read = get_operation("form-read")
    fill = get_operation("form-fill")

    initial = read.execute([PdfInput(form)], read.params_model())
    assert "nome" in initial.meta["fields"]

    filled = fill.execute(
        [PdfInput(form)], fill.params_model(values={"nome": "Davi Moreira"})
    )
    after = read.execute([PdfInput(filled.single.data)], read.params_model())
    assert after.meta["fields"]["nome"] == "Davi Moreira"
