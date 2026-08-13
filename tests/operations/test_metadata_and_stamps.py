"""Testes de metadados, números de página e marca d'água."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe


def _run(name, data, **params):
    op = get_operation(name)
    return op.execute([PdfInput(data)], op.params_model(**params))


def test_metadata_edit_then_read(pdf5):
    edited = _run("metadata-edit", pdf5, title="Meu Documento", author="Davi")
    assert "/Title" in edited.meta["updated"]
    read = _run("metadata-read", edited.single.data)
    meta = read.meta["metadata"]
    assert meta["/Title"] == "Meu Documento"
    assert meta["/Author"] == "Davi"


def test_metadata_read_has_no_artifacts(pdf5):
    result = _run("metadata-read", pdf5)
    assert result.artifacts == []
    assert result.meta["metadata"]["/Pages"] == "5"


def test_page_numbers(pdf5):
    result = _run("page-numbers", pdf5, template="{n}/{total}")
    assert result.meta["numbered"] == 5
    assert pe.count_pages(result.single.data) == 5


def test_page_numbers_invalid_template(pdf5):
    with pytest.raises(ValidationError):
        _run("page-numbers", pdf5, template="{x}")


def test_watermark(pdf5):
    result = _run("watermark", pdf5, text="CONFIDENCIAL", opacity=0.2)
    assert result.meta["stamped"] == 5
    assert pe.count_pages(result.single.data) == 5


def test_watermark_opacity_bounds(pdf5):
    # Acima de 100% é rejeitado (1.0 ratio + 100 = 200% > 100).
    with pytest.raises(ValidationError):
        _run("watermark", pdf5, text="X", opacity=150)
