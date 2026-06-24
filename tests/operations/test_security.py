"""Testes das operações de segurança: protect e unlock."""

from __future__ import annotations

from io import BytesIO

import pytest
from pydantic import ValidationError
from pypdf import PdfReader

from pdftoolkit.core.errors import EncryptedPdfError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe


def _protect(data, **params):
    op = get_operation("protect")
    return op.execute([PdfInput(data)], op.params_model(**params)).single.data


def _unlock(data, **params):
    op = get_operation("unlock")
    return op.execute([PdfInput(data)], op.params_model(**params)).single.data


def test_protect_then_unlock_roundtrip(pdf5):
    locked = _protect(pdf5, user_password="segredo")
    assert PdfReader(BytesIO(locked)).is_encrypted
    unlocked = _unlock(locked, password="segredo")
    assert not PdfReader(BytesIO(unlocked)).is_encrypted
    assert pe.count_pages(unlocked) == 5


def test_unlock_wrong_password(pdf5):
    locked = _protect(pdf5, user_password="segredo")
    with pytest.raises(EncryptedPdfError):
        _unlock(locked, password="errada")


def test_protect_requires_password(pdf5):
    with pytest.raises(ValidationError):
        _protect(pdf5, user_password="")
