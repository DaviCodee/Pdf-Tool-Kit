"""Operação: girar páginas."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import field_validator

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe


class RotateParams(OperationParams):
    degrees: int
    pages: str | None = None
    output_name: str = "rotacionado.pdf"

    @field_validator("degrees")
    @classmethod
    def _multiple_of_90(cls, value: int) -> int:
        if value % 90 != 0 or value == 0:
            raise ValueError("graus deve ser múltiplo de 90 diferente de zero")
        return value


@register
class RotateOperation(PdfOperation[RotateParams]):
    name = "rotate"
    category = "organizar"
    summary = "Gira todas as páginas ou um subconjunto por um múltiplo de 90 graus."
    params_model = RotateParams

    def run(self, inputs: Sequence[PdfInput], params: RotateParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        indices = (
            parse_page_ranges(params.pages, len(writer.pages), unique=True)
            if params.pages is not None
            else None
        )
        pe.rotate_pages(writer, indices, params.degrees)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pages": len(writer.pages)})
