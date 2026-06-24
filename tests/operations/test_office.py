"""Testes das conversões Office (soffice + pdf2docx)."""

from __future__ import annotations

import shutil
from io import BytesIO

import pytest

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe


@pytest.mark.skipif(shutil.which("soffice") is None, reason="LibreOffice não instalado")
def test_office_to_pdf_from_docx():
    docx = pytest.importorskip("docx", reason="python-docx não disponível")
    document = docx.Document()
    document.add_paragraph("Conteúdo de teste do Office.")
    buffer = BytesIO()
    document.save(buffer)

    op = get_operation("office-to-pdf")
    result = op.execute(
        [PdfInput(buffer.getvalue(), "doc.docx")], op.params_model()
    )
    assert result.single.data[:4] == b"%PDF"
    assert pe.count_pages(result.single.data) >= 1


def test_pdf_to_word(pdf3):
    pytest.importorskip("pdf2docx", reason="extra 'office' não instalado")
    op = get_operation("pdf-to-word")
    result = op.execute([PdfInput(pdf3)], op.params_model())
    assert result.single.filename.endswith(".docx")
    assert result.single.data[:2] == b"PK"  # zip (formato OOXML)
