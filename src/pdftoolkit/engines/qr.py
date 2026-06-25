"""Geração de QR codes como imagens PNG (extra ``qr``, requer qrcode[pil]).

Import preguiçoso: o módulo carrega sem o qrcode instalado; o erro só ocorre ao
usar a função, com mensagem orientando a instalar o extra.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any


def _qrcode() -> Any:
    try:
        import qrcode  # type: ignore[import-untyped]
    except ImportError as exc:
        from pdftoolkit.core.errors import MissingDependencyError
        raise MissingDependencyError(
            "geração de QR code requer o extra 'qr' (pip install pdftoolkit[qr])"
        ) from exc
    return qrcode


def make_qr_png(data: str, *, box_size: int = 10, border: int = 1) -> bytes:
    """Gera um QR code para ``data`` e retorna os bytes PNG."""
    qrcode = _qrcode()
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
