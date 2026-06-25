"""Operação: juntar vários PDFs em um só."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import ocr as ocr_engine
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


class MergeFoldersParams(OperationParams):
    output_name: str = "documento-unido.pdf"


@register
class MergeFoldersOperation(PdfOperation[MergeFoldersParams]):
    name = "merge-folders"
    category = "organizar"
    summary = "Junta vários PDFs ordenados alfabeticamente pelo nome do arquivo."
    params_model = MergeFoldersParams
    min_inputs = 2
    max_inputs = None

    def run(self, inputs: Sequence[PdfInput], params: MergeFoldersParams) -> OperationResult:
        sorted_inputs = sorted(inputs, key=lambda x: (x.name or "").lower())
        writer = pe.new_writer()
        for item in sorted_inputs:
            ensure_pdf(item.data, item.name)
            reader = pe.open_reader(item.data)
            pe.add_pages(writer, reader)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(
            artifacts=[artifact],
            meta={"pages": len(writer.pages), "order": [i.name for i in sorted_inputs]},
        )


class MergeOcrParams(OperationParams):
    language: str = "por"
    force: bool = False
    output_name: str = "documento-ocr.pdf"


@register
class MergeOcrOperation(PdfOperation[MergeOcrParams]):
    name = "merge-ocr"
    category = "organizar"
    summary = "Aplica OCR em cada PDF e une todos em um único documento pesquisável."
    params_model = MergeOcrParams
    min_inputs = 2
    max_inputs = None

    def run(self, inputs: Sequence[PdfInput], params: MergeOcrParams) -> OperationResult:
        writer = pe.new_writer()
        pages_total = 0
        for item in inputs:
            ensure_pdf(item.data, item.name)
            ocr_data, _ = ocr_engine.add_text_layer(
                item.data, language=params.language, force=params.force
            )
            reader = pe.open_reader(ocr_data)
            pe.add_pages(writer, reader)
            pages_total += len(reader.pages)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pages": pages_total})
