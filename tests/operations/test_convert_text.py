"""Testes das novas conversões: texto/HTML/Markdown + formatos de imagem extras."""

from __future__ import annotations

from io import BytesIO

import pytest

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe

pytest.importorskip("fitz", reason="extra 'render' não instalado")


def _run(name, datas, **params):
    op = get_operation(name)
    return op.execute([PdfInput(d, "t.pdf") for d in datas], op.params_model(**params))


def test_pdf_to_text_full(pdf3):
    result = _run("pdf-to-text", [pdf3])
    assert result.artifacts[0].media_type == "text/plain"
    text = result.artifacts[0].data.decode("utf-8")
    assert "Y pagina 1" in text
    assert "Y pagina 3" in text


def test_pdf_to_text_subset(pdf5):
    result = _run("pdf-to-text", [pdf5], pages="1,3")
    text = result.artifacts[0].data.decode("utf-8")
    assert "X pagina 1" in text
    assert "X pagina 2" not in text
    assert "X pagina 3" in text


def test_pdf_to_html_self_contained(pdf3):
    result = _run("pdf-to-html", [pdf3])
    html = result.artifacts[0].data.decode("utf-8")
    assert html.startswith("<!DOCTYPE html>")
    assert "Y pagina" in html
    assert "Página 1" in html
    assert "Página 3" in html


def test_pdf_to_json(pdf3):
    pytest.importorskip("pdfplumber", reason="extra 'tables' não instalado")
    result = _run("pdf-to-json", [pdf3])
    import json

    data = json.loads(result.artifacts[0].data)
    assert isinstance(data, list)
    assert len(data) == 3
    assert all("blocks" in page for page in data)


def test_pdf_to_markdown_heading(make_pdf):
    buf = BytesIO()
    from reportlab.pdfgen.canvas import Canvas

    c = Canvas(buf)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(72, 720, "Titulo Grande")
    c.setFont("Helvetica", 12)
    c.drawString(72, 700, "Corpo normal")
    c.showPage()
    c.save()
    pdf = buf.getvalue()
    result = _run("pdf-to-markdown", [pdf])
    md = result.artifacts[0].data.decode("utf-8")
    assert "# Titulo Grande" in md
    assert "Corpo normal" in md


def test_pdf_to_svg(pdf3):
    result = _run("pdf-to-svg", [pdf3])
    assert len(result.artifacts) == 3
    assert all(a.data.startswith(b"<svg") for a in result.artifacts)
    assert all(a.media_type == "image/svg+xml" for a in result.artifacts)


def test_pdf_to_tiff(pdf3):
    pytest.importorskip("PIL", reason="extra 'images' não instalado")
    result = _run("pdf-to-tiff", [pdf3], dpi=72)
    assert len(result.artifacts) == 3
    assert all(a.filename.endswith(".tif") for a in result.artifacts)
    # TIFF little-endian magic: II\x2a\x00
    assert result.artifacts[0].data[:4] == b"II*\x00"


def test_pdf_to_bmp(pdf3):
    pytest.importorskip("PIL", reason="extra 'images' não instalado")
    result = _run("pdf-to-bmp", [pdf3], dpi=72)
    assert len(result.artifacts) == 3
    assert all(a.data[:2] == b"BM" for a in result.artifacts)


def test_pdf_to_webp(pdf3):
    pytest.importorskip("PIL", reason="extra 'images' não instalado")
    result = _run("pdf-to-webp", [pdf3], dpi=72, quality=60)
    assert len(result.artifacts) == 3
    # WebP: RIFF....WEBP
    assert result.artifacts[0].data[:4] == b"RIFF"
    assert result.artifacts[0].data[8:12] == b"WEBP"


def test_pdf_to_ppm(pdf3):
    result = _run("pdf-to-ppm", [pdf3], dpi=72)
    assert len(result.artifacts) == 3
    # PPM ASCII magic: P6
    assert result.artifacts[0].data[:2] == b"P6"


def test_txt_to_pdf():
    op = get_operation("txt-to-pdf")
    result = op.execute([PdfInput(b"Linha 1\nLinha 2\n", "a.txt")], op.params_model())
    assert result.single.data[:4] == b"%PDF"
    assert pe.count_pages(result.single.data) == 1


def test_txt_to_pdf_multi_input():
    op = get_operation("txt-to-pdf")
    result = op.execute(
        [PdfInput(b"primeiro", "a.txt"), PdfInput(b"segundo", "b.txt")],
        op.params_model(),
    )
    text = pe.extract_page_texts(result.single.data)
    assert any("primeiro" in page for page in text)
    assert any("segundo" in page for page in text)


def test_txt_to_pdf_page_size_letter():
    op = get_operation("txt-to-pdf")
    result = op.execute([PdfInput(b"x", "a.txt")], op.params_model(page_size="letter"))
    assert result.single.data[:4] == b"%PDF"


def test_html_to_pdf():
    pytest.importorskip("weasyprint", reason="extra 'html' não instalado")
    op = get_operation("html-to-pdf")
    html = "<html><body><h1>Oi</h1><p>texto</p></body></html>"
    result = op.execute([PdfInput(html.encode("utf-8"), "a.html")], op.params_model())
    assert result.single.data[:4] == b"%PDF"
    assert pe.count_pages(result.single.data) >= 1


def test_pdf_to_xlsx(pdf5):
    pytest.importorskip("openpyxl", reason="extra 'xlsx' não instalado")
    op = get_operation("pdf-to-xlsx")
    result = op.execute([PdfInput(pdf5)], op.params_model())
    # Sem tabelas detectadas: ainda assim gera um xlsx válido.
    assert result.single.data[:2] == b"PK"
    assert result.single.filename.endswith(".xlsx")
