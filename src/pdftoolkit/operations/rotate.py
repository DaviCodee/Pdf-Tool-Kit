"""Operação: girar páginas."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe

# Literal vira `enum` no JSON Schema — hub renderiza <select> automaticamente,
# sem precisar de sidecar config. Inclui os sentidos horário/anti-horário
# porque ambos são úteis (90 vs -90 alinha em direções opostas).
Rotation = Literal[90, -90, 180, -180, 270, -270]


class RotateParams(OperationParams):
    degrees: Rotation
    pages: str | None = None
    output_name: str = "rotacionado.pdf"


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


class BatchRotateParams(OperationParams):
    degrees: Rotation
    pages: str | None = None


@register
class BatchRotateOperation(PdfOperation[BatchRotateParams]):
    name = "batch-rotate"
    category = "organizar"
    summary = "Gira múltiplos PDFs de uma só vez; retorna um arquivo por entrada."
    params_model = BatchRotateParams
    min_inputs = 1
    max_inputs = None

    def run(self, inputs: Sequence[PdfInput], params: BatchRotateParams) -> OperationResult:
        artifacts: list[Artifact] = []
        for item in inputs:
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
            artifacts.append(
                Artifact(data=data, filename=safe_filename(item.name or "rotacionado.pdf"))
            )
        return OperationResult(artifacts=artifacts, meta={"files": len(artifacts)})
