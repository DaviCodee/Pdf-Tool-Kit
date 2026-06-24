"""Operações de manipulação de páginas: remover, extrair e reordenar."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe


def _build(
    reader_data: bytes, indices: Sequence[int], output_name: str
) -> OperationResult:
    writer = pe.new_writer()
    reader = pe.open_reader(reader_data)
    pe.add_pages(writer, reader, list(indices))
    data = pe.write_bytes(writer)
    artifact = Artifact(data=data, filename=safe_filename(output_name))
    return OperationResult(artifacts=[artifact], meta={"pages": len(writer.pages)})


class RemovePagesParams(OperationParams):
    pages: str
    output_name: str = "sem-paginas.pdf"


@register
class RemovePagesOperation(PdfOperation[RemovePagesParams]):
    name = "remove-pages"
    category = "organizar"
    summary = "Remove as páginas indicadas e mantém o restante."
    params_model = RemovePagesParams

    def run(self, inputs: Sequence[PdfInput], params: RemovePagesParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        total = pe.count_pages(item.data)
        to_remove = set(parse_page_ranges(params.pages, total, unique=True))
        kept = [index for index in range(total) if index not in to_remove]
        if not kept:
            raise InvalidInputError("a remoção deixaria o documento sem páginas")
        return _build(item.data, kept, params.output_name)


class ExtractPagesParams(OperationParams):
    pages: str
    output_name: str = "paginas-extraidas.pdf"


@register
class ExtractPagesOperation(PdfOperation[ExtractPagesParams]):
    name = "extract-pages"
    category = "organizar"
    summary = "Cria um novo PDF apenas com as páginas indicadas, na ordem dada."
    params_model = ExtractPagesParams

    def run(self, inputs: Sequence[PdfInput], params: ExtractPagesParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        total = pe.count_pages(item.data)
        indices = parse_page_ranges(params.pages, total)
        return _build(item.data, indices, params.output_name)


class ReorderPagesParams(OperationParams):
    order: str
    output_name: str = "reordenado.pdf"


@register
class ReorderPagesOperation(PdfOperation[ReorderPagesParams]):
    name = "reorder-pages"
    category = "organizar"
    summary = "Reordena o documento segundo uma nova ordem completa de páginas."
    params_model = ReorderPagesParams

    def run(self, inputs: Sequence[PdfInput], params: ReorderPagesParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        total = pe.count_pages(item.data)
        indices = parse_page_ranges(params.order, total)
        if sorted(indices) != list(range(total)):
            raise InvalidInputError(
                "a ordem deve conter cada página exatamente uma vez"
            )
        return _build(item.data, indices, params.output_name)
