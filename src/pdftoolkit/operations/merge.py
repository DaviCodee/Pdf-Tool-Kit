"""Operação: juntar vários PDFs em um só."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe


class MergeParams(OperationParams):
    output_name: str = "documento-unido.pdf"


@register
class MergeOperation(PdfOperation[MergeParams]):
    name = "merge"
    category = "organizar"
    summary = "Junta vários PDFs, na ordem informada, em um único documento."
    params_model = MergeParams
    min_inputs = 2
    max_inputs = None

    def run(self, inputs: Sequence[PdfInput], params: MergeParams) -> OperationResult:
        writer = pe.new_writer()
        for item in inputs:
            ensure_pdf(item.data, item.name)
            reader = pe.open_reader(item.data)
            pe.add_pages(writer, reader)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pages": len(writer.pages)})
