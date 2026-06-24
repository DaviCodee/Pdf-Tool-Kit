"""Fixtures compartilhadas: PDFs gerados em runtime (nada binário é commitado)."""

from __future__ import annotations

from collections.abc import Callable
from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas


def _make_pdf(pages: int = 1, label: str = "P") -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer)
    for index in range(pages):
        canvas.drawString(72, 720, f"{label} pagina {index + 1}")
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


@pytest.fixture
def make_pdf() -> Callable[..., bytes]:
    return _make_pdf


@pytest.fixture
def pdf5() -> bytes:
    return _make_pdf(5, "X")


@pytest.fixture
def pdf3() -> bytes:
    return _make_pdf(3, "Y")
