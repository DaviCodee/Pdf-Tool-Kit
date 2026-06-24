"""Operações de conversão Office: documentos -> PDF e PDF -> Word."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import office

_DOCX_MEDIA = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class OfficeToPdfParams(OperationParams):
    output_name: str = "convertido.pdf"


@register
class OfficeToPdfOperation(PdfOperation[OfficeToPdfParams]):
    name = "office-to-pdf"
    category = "converter"
    summary = "Converte documentos Office (docx/xlsx/pptx/odt...) em PDF via LibreOffice."
    params_model = OfficeToPdfParams

    def run(self, inputs: Sequence[PdfInput], params: OfficeToPdfParams) -> OperationResult:
        item = inputs[0]
        suffix = Path(item.name).suffix
        if not suffix:
            raise InvalidInputError("o arquivo de entrada precisa ter uma extensão (ex.: .docx)")
        data = office.office_to_pdf(item.data, suffix)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"source": suffix.lstrip(".")})


class PdfToWordParams(OperationParams):
    output_name: str = "convertido.docx"


@register
class PdfToWordOperation(PdfOperation[PdfToWordParams]):
    name = "pdf-to-word"
    category = "converter"
    summary = "Converte um PDF em documento Word (.docx)."
    params_model = PdfToWordParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToWordParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = office.pdf_to_docx(item.data)
        artifact = Artifact(
            data=data,
            filename=safe_filename(params.output_name, fallback="convertido.docx"),
            media_type=_DOCX_MEDIA,
        )
        return OperationResult(artifacts=[artifact], meta={"format": "docx"})
