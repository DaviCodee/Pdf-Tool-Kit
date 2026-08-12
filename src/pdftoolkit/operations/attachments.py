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


class AddAttachmentsParams(OperationParams):
    output_name: str = "com-anexos.pdf"

    # Declaração de inputs nomeados pro hub do site renderizar 2 file inputs
    # separados (PDF base + anexos), em vez do único input multi-arquivo
    # genérico. A chave é o field name no FormData; `multiple`/`accept`/`label`
    # controla o <input>. Ops sem `x-inputs` no schema continuam como hoje
    # (um input multi). Veja `js/toolkit-hub.js` para o render.
    model_config = {
        "json_schema_extra": {
            "x-inputs": {
                "base": {
                    "label": "PDF base",
                    "accept": "application/pdf,.pdf",
                    "multiple": False,
                    "required": True,
                },
                "attachments": {
                    "label": "anexos",
                    "accept": "*/*",
                    "multiple": True,
                    "required": True,
                },
            }
        }
    }


@register
class AddAttachmentsOperation(PdfOperation[AddAttachmentsParams]):
    name = "add-attachments"
    category = "editar"
    summary = (
        "Embute 1+ arquivos como anexos no PDF. Envia o PDF base + N anexos; "
        "cada anexo é embutido no PDF de saída (encadeado)."
    )
    params_model = AddAttachmentsParams
    min_inputs = 2       # 1 PDF base + 1+ anexos
    max_inputs = None    # ilimitado

    def run(self, inputs: Sequence[PdfInput], params: AddAttachmentsParams) -> OperationResult:
        base = inputs[0]
        ensure_pdf(base.data, base.name)
        # Encadeia: processa cada attachment sequencialmente, usando o output
        # do anterior como base do próximo. pikepdf precisa reabrir o PDF a
        # cada save (não dá pra acumular anexos em memória sem persistir).
        try:
            current = base.data
            current_name = base.name
            attached: list[str] = []
            for idx, attach in enumerate(inputs[1:], 1):
                # Sanitiza o nome do arquivo para o índice interno.
                name = safe_filename(attach.name or f"anexo-{idx}")
                # Colisão: se já existe um anexo com esse nome, sufixa.
                with pikepdf.open(BytesIO(current)) as pdf:
                    if name in pdf.attachments:
                        stem, dot, ext = name.partition(".")
                        i = 2
                        while f"{stem}-{i}{dot}{ext}" in pdf.attachments:
                            i += 1
                        name = f"{stem}-{i}{dot}{ext}"
                    pdf.attachments[name] = attach.data
                    out = BytesIO()
                    pdf.save(out)
                    current = out.getvalue()
                attached.append(name)
        except Exception as exc:
            raise OperationError(f"falha ao adicionar anexos: {exc}") from exc
        artifact = Artifact(data=current, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"attached": attached, "count": len(attached)})


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
