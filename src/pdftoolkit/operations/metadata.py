"""Operações de metadados: ler e editar as informações do documento."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe

# Mapeia campos amigáveis para as chaves do dicionário de informações do PDF.
_FIELD_KEYS = {
    "title": "/Title",
    "author": "/Author",
    "subject": "/Subject",
    "keywords": "/Keywords",
    "creator": "/Creator",
    "producer": "/Producer",
}


class MetadataReadParams(OperationParams):
    pass


@register
class MetadataReadOperation(PdfOperation[MetadataReadParams]):
    name = "metadata-read"
    category = "info"
    summary = "Lê os metadados (título, autor, etc.) do documento."
    params_model = MetadataReadParams

    def run(self, inputs: Sequence[PdfInput], params: MetadataReadParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        meta = pe.read_metadata(reader)
        meta["/Pages"] = str(len(reader.pages))
        return OperationResult(artifacts=[], meta={"metadata": meta})


class MetadataEditParams(OperationParams):
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: str | None = None
    creator: str | None = None
    producer: str | None = None
    output_name: str = "metadados.pdf"


@register
class MetadataEditOperation(PdfOperation[MetadataEditParams]):
    name = "metadata-edit"
    category = "info"
    summary = "Atualiza os campos de metadados informados, preservando o restante."
    params_model = MetadataEditParams

    def run(self, inputs: Sequence[PdfInput], params: MetadataEditParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        updates = {
            _FIELD_KEYS[field]: value
            for field, value in params.model_dump().items()
            if field in _FIELD_KEYS and value is not None
        }
        if updates:
            pe.set_metadata(writer, updates)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"updated": sorted(updates)})
