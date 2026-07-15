"""Composição de imagens em PDF via Pillow (extra ``images``).

Importação preguiçosa do Pillow.
"""

from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO
from typing import Any

from pdftoolkit.core.errors import InvalidInputError, MissingDependencyError, OperationError

_PIL_FORMATS = {"tiff", "tif", "webp", "bmp", "ppm", "gif", "png", "jpeg", "jpg"}


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


def convert_image(
    raw: bytes,
    target: str,
    *,
    quality: int | None = None,
    lossless: bool = False,
) -> bytes:
    """Re-codifica ``raw`` (PNG ou JPG) para ``target`` (tiff/webp/bmp/...).

    ``target`` é o nome canônico do formato Pillow (``tiff``, ``webp``, ``bmp``,
    ``ppm``, ``gif``...). ``quality`` aplica-se a formatos com perda; ``lossless``
    é respeitado por WebP.
    """
    Image = _pil_image()
    fmt = target.lower().lstrip(".")
    if fmt not in _PIL_FORMATS:
        raise InvalidInputError(f"formato de imagem não suportado: {target!r}")

    try:
        frame = Image.open(BytesIO(raw))
        frame.load()
    except Exception as exc:
        raise InvalidInputError(f"imagem inválida: {exc}") from exc

    # WebP não aceita alfa em algumas versões e BMP/PPM não suportam RGBA.
    if fmt in {"bmp", "ppm", "tiff", "gif"} and frame.mode in {"RGBA", "P", "LA"}:
        frame = frame.convert("RGB")

    save_kwargs: dict[str, Any] = {"format": fmt.upper() if fmt != "jpg" else "JPEG"}
    if fmt in {"jpeg", "jpg"} and quality is not None:
        save_kwargs["quality"] = int(quality)
    if fmt == "webp":
        save_kwargs["lossless"] = bool(lossless)
        if quality is not None:
            save_kwargs["quality"] = int(quality)

    buffer = BytesIO()
    try:
        frame.save(buffer, **save_kwargs)
    except Exception as exc:
        raise OperationError(f"falha ao codificar como {target!r}: {exc}") from exc
    return buffer.getvalue()
