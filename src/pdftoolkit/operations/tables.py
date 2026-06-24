"""Operação: extrair tabelas para CSV."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf
from pdftoolkit.engines import tables as tables_engine


class ExtractTablesParams(OperationParams):
    pass


@register
class ExtractTablesOperation(PdfOperation[ExtractTablesParams]):
    name = "extract-tables"
    category = "converter"
    summary = "Detecta tabelas no PDF e exporta cada uma como CSV."
    params_model = ExtractTablesParams

    def run(self, inputs: Sequence[PdfInput], params: ExtractTablesParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        tables = tables_engine.extract_tables(item.data)
        if not tables:
            raise InvalidInputError("nenhuma tabela encontrada no documento")
        artifacts = [
            Artifact(data=csv_text.encode("utf-8"), filename=name, media_type="text/csv")
            for name, csv_text in tables
        ]
        return OperationResult(artifacts=artifacts, meta={"tables": len(artifacts)})
