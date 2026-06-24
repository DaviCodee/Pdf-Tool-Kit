"""Testes da operação de assinatura (extra sign)."""

from __future__ import annotations

import pytest

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation

pytest.importorskip("pyhanko", reason="extra 'sign' não instalado")


def _sign(data, **params):
    op = get_operation("sign")
    return op.execute([PdfInput(data)], op.params_model(**params))


def test_sign_ephemeral_produces_pdf(pdf3):
    result = _sign(pdf3, ephemeral=True)
    assert result.single.data[:4] == b"%PDF"
    assert len(result.single.data) > len(pdf3)


def test_sign_without_cert_fails(pdf3):
    with pytest.raises(InvalidInputError):
        _sign(pdf3)


def test_sign_invalid_base64_fails(pdf3):
    with pytest.raises(InvalidInputError):
        _sign(pdf3, pkcs12_base64="!!!nao-base64!!!")
