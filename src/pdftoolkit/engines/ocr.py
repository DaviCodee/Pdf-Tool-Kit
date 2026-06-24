"""Camada de texto via OCR usando ocrmypdf (extra ``ocr`` + tesseract no sistema)."""

from __future__ import annotations

from typing import Any

from pdftoolkit.core.errors import MissingDependencyError, OperationError
from pdftoolkit.core.workspace import temp_workspace


def _ocrmypdf() -> Any:
    try:
        import ocrmypdf
    except ImportError as exc:
        raise MissingDependencyError(
            "OCR requer o extra 'ocr' (pip install pdftoolkit[ocr]) e o tesseract instalado"
        ) from exc
    return ocrmypdf


def add_text_layer(data: bytes, *, language: str = "por", force: bool = False) -> bytes:
    """Adiciona uma camada de texto pesquisável ao PDF.

    Por padrão pula páginas que já possuem texto; ``force`` re-rasteriza tudo.
    """
    ocrmypdf = _ocrmypdf()
    with temp_workspace() as workspace:
        source = workspace / "entrada.pdf"
        target = workspace / "saida.pdf"
        source.write_bytes(data)
        options: dict[str, Any] = {"language": language, "progress_bar": False}
        if force:
            options["force_ocr"] = True
        else:
            options["skip_text"] = True
        try:
            ocrmypdf.ocr(str(source), str(target), **options)
        except MissingDependencyError:
            raise
        except Exception as exc:
            raise OperationError(f"falha no OCR: {exc}") from exc
        return target.read_bytes()
