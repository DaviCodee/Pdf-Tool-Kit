"""Testes das operações de conversão (precisam dos extras render/images)."""

from __future__ import annotations

from io import BytesIO

import pytest

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.registry import get_operation
from pdftoolkit.engines import pypdf_engine as pe

pytest.importorskip("fitz", reason="extra 'render' não instalado")


def _run(name, datas, **params):
    op = get_operation(name)
    return op.execute([PdfInput(d) for d in datas], op.params_model(**params))


def test_pdf_to_image_per_page(pdf3):
    result = _run("pdf-to-image", [pdf3], dpi=72)
    assert len(result.artifacts) == 3
    assert all(a.media_type == "image/png" for a in result.artifacts)
    assert result.artifacts[0].data[:4] == b"\x89PNG"


def test_pdf_to_image_jpg_subset(pdf5):
    result = _run("pdf-to-image", [pdf5], format="jpg", dpi=72, pages="1,3")
    assert [a.filename for a in result.artifacts] == ["pagina-001.jpg", "pagina-003.jpg"]
    assert result.artifacts[0].media_type == "image/jpeg"


def test_thumbnail_defaults_to_first_page(pdf5):
    result = _run("thumbnail", [pdf5], width=100)
    assert len(result.artifacts) == 1
    assert result.artifacts[0].filename == "miniatura-001.png"


def test_images_to_pdf_roundtrip(pdf3):
    images = [a.data for a in _run("pdf-to-image", [pdf3], dpi=72).artifacts]
    op = get_operation("images-to-pdf")
    pytest.importorskip("PIL", reason="extra 'images' não instalado")
    result = op.execute([PdfInput(d, "p.png") for d in images], op.params_model())
    assert pe.count_pages(result.single.data) == 3


def test_images_to_pdf_rejects_non_image():
    pytest.importorskip("PIL", reason="extra 'images' não instalado")
    op = get_operation("images-to-pdf")
    with pytest.raises(InvalidInputError):
        op.execute([PdfInput(b"isto nao e imagem", "x.png")], op.params_model())


def test_pdf_to_image_produces_real_image(pdf3):
    pytest.importorskip("PIL", reason="extra 'images' não instalado")
    from PIL import Image

    png = _run("pdf-to-image", [pdf3], dpi=72).artifacts[0].data
    assert Image.open(BytesIO(png)).format == "PNG"
