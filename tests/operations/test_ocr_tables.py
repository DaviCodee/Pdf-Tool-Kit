"""Testes de OCR (extra ocr + tesseract) e extração de tabelas (extra tables)."""

from __future__ import annotations

import shutil
from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe


def _table_pdf() -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    xs = [80, 200, 320]
    ys = [700, 670, 640]
    for x in xs:
        canvas.line(x, ys[-1], x, ys[0])
    for y in ys:
        canvas.line(xs[0], y, xs[-1], y)
    rows = [["A", "B"], ["1", "2"]]
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            canvas.drawString(xs[c] + 5, ys[r] - 18, value)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


@pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract não instalado"
)
def test_ocr_runs_and_keeps_pages(pdf3):
    pytest.importorskip("ocrmypdf", reason="extra 'ocr' não instalado")
    op = get_operation("ocr")
    result = op.execute([PdfInput(pdf3)], op.params_model(language="por"))
    assert pe.count_pages(result.single.data) == 3


@pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract não instalado"
)
def test_ocr_warns_when_all_pages_already_have_text(pdf3):
    pytest.importorskip("ocrmypdf", reason="extra 'ocr' não instalado")
    op = get_operation("ocr")
    result = op.execute([PdfInput(pdf3)], op.params_model(language="por"))
    assert result.meta["paginas_totais"] == 3
    assert result.meta["paginas_ja_com_texto"] == 3
    assert result.meta["paginas_processadas"] == 0
    assert "aviso" in result.meta


@pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract não instalado"
)
def test_ocr_force_reprocesses_and_omits_warning(pdf3):
    pytest.importorskip("ocrmypdf", reason="extra 'ocr' não instalado")
    op = get_operation("ocr")
    result = op.execute([PdfInput(pdf3)], op.params_model(language="por", force=True))
    assert result.meta["paginas_processadas"] == 3
    assert "aviso" not in result.meta


def test_extract_tables_to_csv():
    pytest.importorskip("pdfplumber", reason="extra 'tables' não instalado")
    op = get_operation("extract-tables")
    result = op.execute([PdfInput(_table_pdf())], op.params_model())
    assert result.meta["tables"] >= 1
    assert result.artifacts[0].media_type == "text/csv"
    assert "A,B" in result.artifacts[0].data.decode()


def test_extract_tables_none_found(pdf3):
    pytest.importorskip("pdfplumber", reason="extra 'tables' não instalado")
    op = get_operation("extract-tables")
    with pytest.raises(InvalidInputError):
        op.execute([PdfInput(pdf3)], op.params_model())
