"""Conversões Office: documentos -> PDF (LibreOffice) e PDF -> Word (pdf2docx)."""

from __future__ import annotations

from typing import Any

from pdftoolkit.core.errors import MissingDependencyError, OperationError
from pdftoolkit.core.process import require_binary, run_command
from pdftoolkit.core.workspace import temp_workspace


def office_to_pdf(data: bytes, suffix: str) -> bytes:
    """Converte um documento Office (docx/xlsx/pptx/odt...) em PDF via soffice."""
    binary = require_binary("soffice")
    clean_suffix = suffix.lstrip(".") or "doc"
    with temp_workspace() as workspace:
        source = workspace / f"entrada.{clean_suffix}"
        source.write_bytes(data)
        profile = workspace / "lo-profile"
        run_command(
            [
                binary,
                "--headless",
                f"-env:UserInstallation=file://{profile}",
                "--convert-to",
                "pdf",
                "--outdir",
                str(workspace),
                str(source),
            ],
            cwd=workspace,
            timeout=180,
        )
        result = workspace / "entrada.pdf"
        if not result.exists():
            raise OperationError("a conversão não produziu um PDF")
        return result.read_bytes()


def _converter() -> Any:
    try:
        from pdf2docx import Converter
    except ImportError as exc:
        raise MissingDependencyError(
            "conversão PDF->Word requer o extra 'office' (pip install pdftoolkit[office])"
        ) from exc
    return Converter


def pdf_to_docx(data: bytes) -> bytes:
    """Converte um PDF em um documento Word (.docx)."""
    converter_cls = _converter()
    with temp_workspace() as workspace:
        source = workspace / "entrada.pdf"
        target = workspace / "saida.docx"
        source.write_bytes(data)
        converter = converter_cls(str(source))
        try:
            converter.convert(str(target))
        except Exception as exc:
            raise OperationError(f"falha ao converter para Word: {exc}") from exc
        finally:
            converter.close()
        return target.read_bytes()
