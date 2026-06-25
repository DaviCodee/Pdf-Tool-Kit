"""Operações de anexos embutidos em PDF."""

from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO

import pikepdf

from pdftoolkit.core.errors import OperationError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename


class ListAttachmentsParams(OperationParams):
    pass


@register
class ListAttachmentsOperation(PdfOperation[ListAttachmentsParams]):
    name = "list-attachments"
    category = "info"
    summary = "Lista os arquivos embutidos (anexos) do PDF."
    params_model = ListAttachmentsParams

    def run(self, inputs: Sequence[PdfInput], params: ListAttachmentsParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        try:
            with pikepdf.open(BytesIO(item.data)) as pdf:
                names = list(pdf.attachments.keys())
            return OperationResult(artifacts=[], meta={"attachments": names, "count": len(names)})
        except Exception as exc:
            raise OperationError(f"falha ao listar anexos: {exc}") from exc


class AddAttachmentParams(OperationParams):
    filename: str
    output_name: str = "com-anexo.pdf"


@register
class AddAttachmentOperation(PdfOperation[AddAttachmentParams]):
    name = "add-attachment"
    category = "editar"
    summary = "Embute o segundo arquivo como anexo no PDF. Informe 'filename' para o nome interno."
    params_model = AddAttachmentParams
    min_inputs = 2
    max_inputs = 2

    def run(self, inputs: Sequence[PdfInput], params: AddAttachmentParams) -> OperationResult:
        base, attach = inputs[0], inputs[1]
        ensure_pdf(base.data, base.name)
        try:
            with pikepdf.open(BytesIO(base.data)) as pdf:
                name = safe_filename(params.filename, fallback=attach.name or "anexo")
                pdf.attachments[name] = attach.data
                out = BytesIO()
                pdf.save(out)
                data = out.getvalue()
        except Exception as exc:
            raise OperationError(f"falha ao adicionar anexo: {exc}") from exc
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"attached": name})


class ExtractAttachmentParams(OperationParams):
    pass


@register
class ExtractAttachmentOperation(PdfOperation[ExtractAttachmentParams]):
    name = "extract-attachment"
    category = "editar"
    summary = "Extrai todos os arquivos embutidos do PDF como artefatos separados."
    params_model = ExtractAttachmentParams

    def run(self, inputs: Sequence[PdfInput], params: ExtractAttachmentParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        try:
            with pikepdf.open(BytesIO(item.data)) as pdf:
                artifacts: list[Artifact] = []
                for name in pdf.attachments:
                    filespec = pdf.attachments[name]
                    attached_file = filespec.get_file()
                    content = bytes(attached_file.read_bytes())
                    artifacts.append(
                        Artifact(data=content, filename=safe_filename(name, fallback="anexo"))
                    )
        except Exception as exc:
            raise OperationError(f"falha ao extrair anexos: {exc}") from exc
        return OperationResult(artifacts=artifacts, meta={"extracted": len(artifacts)})
