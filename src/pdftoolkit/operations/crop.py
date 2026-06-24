"""Operação: recortar a área visível das páginas (cropbox)."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import model_validator

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe


class CropParams(OperationParams):
    """Caixa de corte em pontos PDF (origem no canto inferior esquerdo)."""

    left: float
    bottom: float
    right: float
    top: float
    pages: str | None = None
    output_name: str = "recortado.pdf"

    @model_validator(mode="after")
    def _valid_box(self) -> CropParams:
        if self.right <= self.left:
            raise ValueError("'right' deve ser maior que 'left'")
        if self.top <= self.bottom:
            raise ValueError("'top' deve ser maior que 'bottom'")
        return self


@register
class CropOperation(PdfOperation[CropParams]):
    name = "crop"
    category = "organizar"
    summary = "Define a caixa de corte (área visível) das páginas."
    params_model = CropParams

    def run(self, inputs: Sequence[PdfInput], params: CropParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        indices = (
            parse_page_ranges(params.pages, len(writer.pages), unique=True)
            if params.pages is not None
            else None
        )
        box = (params.left, params.bottom, params.right, params.top)
        pe.set_crop(writer, indices, box)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pages": len(writer.pages)})
