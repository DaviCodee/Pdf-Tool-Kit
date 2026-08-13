"""Testes de layout: nup + page-size (validam Literals adicionados)."""

from __future__ import annotations

from io import BytesIO

import pytest
from pydantic import ValidationError
from reportlab.pdfgen.canvas import Canvas

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation


def _text_pdf(text: str = "x", pages: int = 1) -> bytes:
    buf = BytesIO()
    canvas = Canvas(buf)
    for i in range(pages):
        canvas.drawString(72, 720, f"{text} {i + 1}")
        canvas.showPage()
    canvas.save()
    return buf.getvalue()


def test_nup_accepts_valid_papers():
    """NupParams.paper aceita só os 5 Literals."""
    op = get_operation("nup")
    for paper in ("a3", "a4", "a5", "letter", "legal"):
        params = op.params_model(paper=paper, n=2)
        assert params.paper == paper


def test_nup_rejects_invalid_paper():
    """Paper fora da enum é rejeitado pelo Literal."""
    op = get_operation("nup")
    with pytest.raises(ValidationError):
        op.params_model(paper="tabloid", n=2)  # tabloid não é válido pra nup
    with pytest.raises(ValidationError):
        op.params_model(paper="A4", n=2)  # case-sensitive


def test_nup_schema_carries_enum_branches():
    """Nup schema: paper tem os 5 presets no enum (anyOf ou top-level)."""
    op = get_operation("nup")
    schema = op.params_model.model_json_schema()
    prop = schema["properties"]["paper"]
    if "enum" in prop:
        assert prop["enum"] == ["a3", "a4", "a5", "letter", "legal"]
    else:
        found = [b["enum"] for b in prop.get("anyOf", []) if "enum" in b]
        assert found and found[0] == ["a3", "a4", "a5", "letter", "legal"]


def test_page_size_accepts_all_presets():
    """PageSizeParams.preset aceita os 6 Literals (incluindo tabloid)."""
    op = get_operation("page-size")
    for preset in ("a3", "a4", "a5", "letter", "legal", "tabloid"):
        params = op.params_model(preset=preset)
        assert params.preset == preset


def test_page_size_rejects_invalid_preset():
    """Preset fora da enum é rejeitado."""
    op = get_operation("page-size")
    with pytest.raises(ValidationError):
        op.params_model(preset="a6")


def test_page_size_schema_carries_enum():
    """JSON Schema expõe os 6 presets no enum (qualquer das anyOf branches)."""
    op = get_operation("page-size")
    schema = op.params_model.model_json_schema()
    # Optional[Literal] vira anyOf [enum, null-type]. Aceitamos qualquer branch.
    found_enum = None
    for branch in schema["properties"]["preset"].get("anyOf", []):
        if "enum" in branch:
            found_enum = branch["enum"]
            break
    assert found_enum == ["a3", "a4", "a5", "letter", "legal", "tabloid"]


def test_nup_schema_carries_enum_branches():
    """Nup schema: paper tem os 5 presets no enum (anyOf ou top-level)."""
    op = get_operation("nup")
    schema = op.params_model.model_json_schema()
    prop = schema["properties"]["paper"]
    if "enum" in prop:
        assert prop["enum"] == ["a3", "a4", "a5", "letter", "legal"]
    else:
        found = [b["enum"] for b in prop.get("anyOf", []) if "enum" in b]
        assert found and found[0] == ["a3", "a4", "a5", "letter", "legal"]


def test_page_size_requires_preset_or_dimensions():
    """Sem preset E sem width/height → ValidationError."""
    op = get_operation("page-size")
    with pytest.raises(ValidationError):
        op.params_model()


def test_nup_end_to_end_runs():
    """Nup aceita uma config válida e roda sem erro."""
    op = get_operation("nup")
    pdf = _text_pdf(pages=4)
    result = op.execute([PdfInput(pdf, "in.pdf")], op.params_model(n=2, paper="a4"))
    assert result.artifacts
    assert result.meta["n"] == 2
    assert result.meta["output_pages"] == 2  # ceil(4 / 2)
