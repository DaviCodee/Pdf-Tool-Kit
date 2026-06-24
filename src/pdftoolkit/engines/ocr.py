"""Camada de texto via OCR usando ocrmypdf (extra ``ocr`` + tesseract no sistema)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from pypdf import PdfReader

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


def _pages_with_text(reader: PdfReader) -> int:
    """Conta páginas que já possuem alguma camada de texto extraível."""
    return sum(1 for page in reader.pages if (page.extract_text() or "").strip())


def add_text_layer(
    data: bytes, *, language: str = "por", force: bool = False
) -> tuple[bytes, dict[str, Any]]:
    """Adiciona uma camada de texto pesquisável ao PDF.

    Por padrão pula páginas que já possuem texto; ``force`` re-rasteriza tudo.

    Retorna os bytes do PDF e metadados sobre o que foi processado.
    """
    ocrmypdf = _ocrmypdf()
    with temp_workspace() as workspace:
        source = workspace / "entrada.pdf"
        target = workspace / "saida.pdf"
        source.write_bytes(data)

        reader = PdfReader(BytesIO(data))
        total_pages = len(reader.pages)
        pages_with_text = _pages_with_text(reader)

        options: dict[str, Any] = {"language": language, "progress_bar": False}
        if force:
            options["force_ocr"] = True
            ocred = total_pages
        else:
            options["skip_text"] = True
            ocred = total_pages - pages_with_text
        try:
            ocrmypdf.ocr(str(source), str(target), **options)
        except MissingDependencyError:
            raise
        except Exception as exc:
            raise OperationError(f"falha no OCR: {exc}") from exc

        meta: dict[str, Any] = {
            "language": language,
            "force": force,
            "paginas_totais": total_pages,
            "paginas_processadas": ocred,
            "paginas_ja_com_texto": pages_with_text,
        }
        if not force and ocred == 0:
            meta["aviso"] = (
                "Nenhuma página foi processada: todas já possuíam texto. "
                "O arquivo de saída é uma cópia. Use --force para re-rasterizar "
                "e refazer o OCR mesmo assim."
            )
        return target.read_bytes(), meta
