"""Extração de tabelas para CSV via pdfplumber (extra ``tables``)."""

from __future__ import annotations

import csv
import io
from typing import Any

from pdftoolkit.core.errors import MissingDependencyError, OperationError


def _pdfplumber() -> Any:
    try:
        import pdfplumber
    except ImportError as exc:
        raise MissingDependencyError(
            "extração de tabelas requer o extra 'tables' (pip install pdftoolkit[tables])"
        ) from exc
    return pdfplumber


def extract_tables(data: bytes) -> list[tuple[str, str]]:
    """Retorna pares ``(nome, csv)`` para cada tabela detectada no documento."""
    pdfplumber = _pdfplumber()
    results: list[tuple[str, str]] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                for table_number, table in enumerate(page.extract_tables(), start=1):
                    name = f"pagina-{page_number:03d}-tabela-{table_number}.csv"
                    results.append((name, _to_csv(table)))
    except Exception as exc:  # pragma: no cover - entrada corrompida
        raise OperationError(f"falha ao extrair tabelas: {exc}") from exc
    return results


def _to_csv(rows: list[list[str | None]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(["" if cell is None else cell for cell in row])
    return buffer.getvalue()
