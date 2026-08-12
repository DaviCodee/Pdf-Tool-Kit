"""Testes do motor pikepdf_engine.list_fonts — enumeração enriquecida."""

from __future__ import annotations

from io import BytesIO

import pikepdf
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.engines.pikepdf_engine import (
    _split_basename,
    list_fonts,
)


def _text_pdf(text: str) -> bytes:
    buf = BytesIO()
    canvas = Canvas(buf)
    canvas.drawString(72, 720, text)
    canvas.showPage()
    canvas.save()
    return buf.getvalue()


def test_split_basename_plain():
    """Sem prefixo de subset, sem sufixo de estilo."""
    assert _split_basename("/Helvetica") == (None, "Helvetica", "")


def test_split_basename_with_style():
    """Sufixo -Bold separa estilo."""
    assert _split_basename("/Helvetica-Bold") == (None, "Helvetica", "Bold")


def test_split_basename_with_subset_prefix():
    """Schema padrão ABCDEF+Family-Style."""
    assert _split_basename("/ABCDEF+Helvetica-Bold") == ("ABCDEF", "Helvetica", "Bold")


def test_split_basename_longest_suffix_wins():
    """-BoldOblique é mais longo que -Bold — ganha na hora de strip."""
    subset, family, style = _split_basename("/ABCDEF+Helvetica-BoldOblique")
    assert subset == "ABCDEF"
    assert family == "Helvetica"
    assert style == "BoldOblique"


def test_split_basename_rgb_italic():
    subset, family, style = _split_basename("/DejaVuSans")
    assert (subset, family, style) == (None, "DejaVuSans", "")


def test_list_fonts_empty_pdf():
    """PDF sem /Resources/Font devolve lista vazia."""
    # Cria PDF sem usar reportlab (sem fontes default) usando pikepdf direto.
    pdf = pikepdf.Pdf.new()
    pdf.pages.append(pikepdf.Page(pikepdf.Dictionary(Type=pikepdf.Name.Page)))
    out = BytesIO()
    pdf.save(out)
    fonts = list_fonts(out.getvalue())
    assert fonts == []


def test_list_fonts_inspects_basename_and_subtype():
    """reportlab embute Helvetica — confirmamos name/subtype preenchidos."""
    fonts = list_fonts(_text_pdf("test"))
    # reportlab com default usa Helvetica (PostScript Type1) e uma font
    # built-in. Devemos ter ao menos 1 font.
    assert len(fonts) >= 1
    # shapes das keys
    for f in fonts:
        assert {"name", "family", "style", "subset", "subtype", "encoding", "embedded"} <= set(f.keys())


def test_list_fonts_returns_consistent_family_for_subset():
    """Subset prefix é preservado em `subset` mas `family`/`style` vêm stripped."""
    # Injeta uma font com subset prefix no /Resources de uma página.
    buf = BytesIO()
    canvas = Canvas(buf)
    canvas.drawString(72, 720, "x")
    canvas.showPage()
    canvas.save()
    with pikepdf.open(BytesIO(buf.getvalue())) as pdf:
        page = pdf.pages[0]
        resources = page.obj.get("/Resources", {})
        if "/Font" not in resources:
            resources["/Font"] = pikepdf.Dictionary()
        resources["/Font"]["/F1"] = pikepdf.Dictionary(
            BaseFont=pikepdf.Name("/ABCDEF+MyFont-Bold"),
            Subtype=pikepdf.Name("/Type1"),
        )
        page.obj["/Resources"] = resources
        out = BytesIO()
        pdf.save(out)
    fonts = list_fonts(out.getvalue())
    names = [f["name"] for f in fonts]
    assert "ABCDEF+MyFont-Bold" in names
    entry = next(f for f in fonts if f["name"] == "ABCDEF+MyFont-Bold")
    assert entry["family"] == "MyFont"
    assert entry["style"] == "Bold"
    assert entry["subset"] == "ABCDEF"
    assert entry["subtype"] == "Type1"


def test_list_fonts_embedded_marker():
    """/FontDescriptor com /FontFile2 marca a fonte como embedded."""
    buf = BytesIO()
    canvas = Canvas(buf)
    canvas.drawString(72, 720, "x")
    canvas.showPage()
    canvas.save()
    with pikepdf.open(BytesIO(buf.getvalue())) as pdf:
        page = pdf.pages[0]
        resources = page.obj.get("/Resources", {})
        if "/Font" not in resources:
            resources["/Font"] = pikepdf.Dictionary()
        # `pikepdf.Stream` precisa do owner (Pdf) — sem isso não aceita bytes.
        font_stream = pikepdf.Stream(pdf, b"OTTO\x00\x01fake cff")
        font_obj = pikepdf.Dictionary(
            BaseFont=pikepdf.Name("/ABCDEF+EmbeddedFont"),
            Subtype=pikepdf.Name("/Type1"),
            FontDescriptor=pikepdf.Dictionary(
                FontFile3=font_stream,
            ),
        )
        resources["/Font"]["/F1"] = font_obj
        page.obj["/Resources"] = resources
        out = BytesIO()
        pdf.save(out)
    fonts = list_fonts(out.getvalue())
    entry = next(f for f in fonts if f["name"] == "ABCDEF+EmbeddedFont")
    assert entry["embedded"] is True
    assert entry["subtype"] == "Type1"
