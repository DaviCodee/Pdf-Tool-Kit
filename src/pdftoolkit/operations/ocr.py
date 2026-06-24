"""Operação: adicionar camada de texto via OCR."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import ocr as ocr_engine


class OcrParams(OperationParams):
    language: str = "por"
    force: bool = False
    output_name: str = "ocr.pdf"


@register
class OcrOperation(PdfOperation[OcrParams]):
    name = "ocr"
    category = "converter"
    summary = "Adiciona uma camada de texto pesquisável a um PDF escaneado."
    params_model = OcrParams

    def run(self, inputs: Sequence[PdfInput], params: OcrParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = ocr_engine.add_text_layer(
            item.data, language=params.language, force=params.force
        )
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"language": params.language})
