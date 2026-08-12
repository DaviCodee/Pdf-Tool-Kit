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
    # form-read agora devolve lista de {name, type, value, ...} — uma entry por campo.
    assert isinstance(initial.meta["fields"], list)
    assert any(f["name"] == "nome" for f in initial.meta["fields"])
    nome = next(f for f in initial.meta["fields"] if f["name"] == "nome")
    assert nome["type"] == "text"

    # fill-form ainda aceita dict[str, str] pra retro-compat.
    filled = fill.execute(
        [PdfInput(form)], fill.params_model(values={"nome": "Davi Moreira"})
    )
    after = read.execute([PdfInput(filled.single.data)], read.params_model())
    after_nome = next(f for f in after.meta["fields"] if f["name"] == "nome")
    assert after_nome["value"] == "Davi Moreira"


def test_form_read_text_field_metadata():
    """form-read devolve type/value/options/required/rect por campo."""
    form = _form_pdf()
    read = get_operation("form-read")
    result = read.execute([PdfInput(form)], read.params_model())
    fields = result.meta["fields"]
    assert result.meta["count"] == 1
    assert fields[0]["name"] == "nome"
    assert fields[0]["type"] == "text"
    assert fields[0]["options"] is None
    assert fields[0]["required"] is False
    # /Rect presente (4 floats: x, y, w, h).
    assert fields[0]["rect"] is not None and len(fields[0]["rect"]) == 4


def test_form_read_no_fields_returns_empty_list():
    """PDF sem form devolve lista vazia (não dict)."""
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas
    buf = BytesIO()
    c = Canvas(buf); c.drawString(72, 720, "no form here"); c.showPage(); c.save()
    plain = buf.getvalue()
    read = get_operation("form-read")
    result = read.execute([PdfInput(plain)], read.params_model())
    assert result.meta["fields"] == []
    assert result.meta["count"] == 0
