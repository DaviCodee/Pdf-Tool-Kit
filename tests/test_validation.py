"""Testes de validação de entrada e nomes de arquivo."""

from __future__ import annotations

import pytest

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.validation import (
    ensure_pdf,
    looks_like_pdf,
    safe_filename,
    with_suffix,
)


def test_looks_like_pdf():
    assert looks_like_pdf(b"%PDF-1.7\n...")
    assert not looks_like_pdf(b"not a pdf")


def test_ensure_pdf_rejects_non_pdf():
    with pytest.raises(InvalidInputError):
        ensure_pdf(b"texto qualquer", "x.txt")


def test_ensure_pdf_rejects_empty():
    with pytest.raises(InvalidInputError):
        ensure_pdf(b"", "vazio.pdf")


def test_safe_filename_strips_path_and_specials():
    assert safe_filename("../../etc/pa ss wd.pdf") == "pa_ss_wd.pdf"
    assert safe_filename("") == "documento.pdf"


def test_with_suffix():
    assert with_suffix("doc.pdf", "-out") == "doc-out.pdf"
    assert with_suffix("semext", "-out") == "semext-out"
