"""Composição de imagens em PDF via Pillow (extra ``images``).

Importação preguiçosa do Pillow.
"""

from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO
from typing import Any

from pdftoolkit.core.errors import InvalidInputError, MissingDependencyError


def _pil_image() -> Any:
    try:
        from PIL import Image
    except ImportError as exc:
        raise MissingDependencyError(
            "conversão de imagens requer o extra 'images' (pip install pdftoolkit[images])"
        ) from exc
    return Image


def images_to_pdf(images: Sequence[bytes], *, dpi: int = 150) -> bytes:
    """Cria um PDF com uma página por imagem (cada página no tamanho da imagem)."""
    Image = _pil_image()
    if not images:
        raise InvalidInputError("nenhuma imagem fornecida")

    frames = []
    for position, raw in enumerate(images, start=1):
        try:
            frame = Image.open(BytesIO(raw))
            frame.load()
        except Exception as exc:
            raise InvalidInputError(f"imagem inválida na posição {position}") from exc
        if frame.mode in {"RGBA", "P", "LA"}:
            frame = frame.convert("RGB")
        frames.append(frame)

    buffer = BytesIO()
    first, rest = frames[0], frames[1:]
    first.save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=rest,
        resolution=float(dpi),
    )
    return buffer.getvalue()
