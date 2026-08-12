"""Testes das operações de anexos (add-attachment, add-attachments, extract, list)."""

from __future__ import annotations

from io import BytesIO

import pikepdf
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation


def _pdf_with_text(text: str) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    canvas.drawString(72, 720, text)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def _add_attachment(pdf: bytes, attachment: bytes, *, filename: str = "") -> bytes:
    op = get_operation("add-attachment")
    params = op.params_model(filename=filename) if filename else op.params_model(filename="x.txt")
    return op.execute(
        [PdfInput(pdf, "base.pdf"), PdfInput(attachment, "anexo.bin")], params
    ).single.data


def test_add_attachment_singular_roundtrip():
    """1 PDF + 1 attachment binário → PDF resultante tem o anexo embutido."""
    base = _pdf_with_text("base")
    payload = b"conteudo do anexo"
    out = _add_attachment(base, payload, filename="notas.txt")
    with pikepdf.open(BytesIO(out)) as pdf:
        assert "notas.txt" in pdf.attachments
        assert bytes(pdf.attachments["notas.txt"].get_file().read_bytes()) == payload


def test_add_attachments_multiple_roundtrip():
    """1 PDF + 3 attachments → PDF resultante tem os 3 embutidos."""
    base = _pdf_with_text("base")
    a1 = b"primeiro anexo"
    a2 = b"segundo anexo bem maior e mais pesado"
    a3 = bytes(range(64))  # binário qualquer
    op = get_operation("add-attachments")
    out = op.execute(
        [
            PdfInput(base, "base.pdf"),
            PdfInput(a1, "a1.txt"),
            PdfInput(a2, "a2.txt"),
            PdfInput(a3, "a3.bin"),
        ],
        op.params_model(),
    ).single.data
    with pikepdf.open(BytesIO(out)) as pdf:
        names = sorted(pdf.attachments.keys())
        assert names == ["a1.txt", "a2.txt", "a3.bin"]
        assert bytes(pdf.attachments["a1.txt"].get_file().read_bytes()) == a1
        assert bytes(pdf.attachments["a2.txt"].get_file().read_bytes()) == a2
        assert bytes(pdf.attachments["a3.bin"].get_file().read_bytes()) == a3
    meta = op.execute(
        [
            PdfInput(base, "base.pdf"),
            PdfInput(a1, "a1.txt"),
            PdfInput(a2, "a2.txt"),
        ],
        op.params_model(),
    ).meta
    assert meta["count"] == 2
    assert set(meta["attached"]) == {"a1.txt", "a2.txt"}


def test_add_attachments_collision_appends_suffix():
    """Anexos com mesmo nome em sequência recebem sufixo."""
    base = _pdf_with_text("base")
    a1 = b"primeiro"
    a2 = b"segundo"
    op = get_operation("add-attachments")
    # a1 e a2 têm o mesmo nome "dup.txt" — teste a colisão.
    out = op.execute(
        [
            PdfInput(base, "base.pdf"),
            PdfInput(a1, "dup.txt"),
            PdfInput(a2, "dup.txt"),
        ],
        op.params_model(),
    ).single.data
    with pikepdf.open(BytesIO(out)) as pdf:
        names = sorted(pdf.attachments.keys())
        assert names == ["dup-2.txt", "dup.txt"]
        assert bytes(pdf.attachments["dup.txt"].get_file().read_bytes()) == a1
        assert bytes(pdf.attachments["dup-2.txt"].get_file().read_bytes()) == a2


def test_add_attachments_min_inputs_two():
    """Sem anexo (apenas PDF) o op rejeita — min_inputs=2."""
    base = _pdf_with_text("base")
    op = get_operation("add-attachments")
    import pytest
    with pytest.raises(InvalidInputError):
        op.execute([PdfInput(base, "base.pdf")], op.params_model())


def test_add_attachments_schema_includes_x_inputs():
    """Schema expõe `x-inputs` para o hub renderizar 2 inputs nomeados."""
    op = get_operation("add-attachments")
    schema = op.params_model.model_json_schema()
    assert "x-inputs" in schema
    x = schema["x-inputs"]
    assert "base" in x and "attachments" in x
    assert x["base"]["multiple"] is False
    assert x["attachments"]["multiple"] is True
    assert x["base"]["required"] is True
    assert x["attachments"]["required"] is True
    assert "pdf" in x["base"]["accept"].lower()
