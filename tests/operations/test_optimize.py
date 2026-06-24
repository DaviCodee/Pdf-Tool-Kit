"""Testes das operações de otimização (compress requer Ghostscript)."""

from __future__ import annotations

import shutil

import pytest

from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe


def _run(name, data, **params):
    op = get_operation(name)
    return op.execute([PdfInput(data)], op.params_model(**params))


def test_optimize_web_keeps_pages(pdf5):
    result = _run("optimize-web", pdf5)
    assert result.meta["linearized"] is True
    assert pe.count_pages(result.single.data) == 5


@pytest.mark.skipif(shutil.which("gs") is None, reason="Ghostscript não instalado")
def test_compress_returns_valid_pdf(pdf5):
    result = _run("compress", pdf5, quality="screen")
    assert pe.count_pages(result.single.data) == 5
    assert "original_bytes" in result.meta and "result_bytes" in result.meta
