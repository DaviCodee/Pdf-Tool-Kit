"""Operações de manipulação de páginas: remover, extrair, reordenar, inserir."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe
from pdftoolkit.engines import render as render_engine


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


class InsertPagesParams(OperationParams):
    position: int = Field(ge=0, default=0)
    output_name: str = "inserido.pdf"


@register
class InsertPagesOperation(PdfOperation[InsertPagesParams]):
    name = "insert-pages"
    category = "organizar"
    summary = "Insere todas as páginas do segundo PDF dentro do primeiro, na posição indicada."
    params_model = InsertPagesParams
    min_inputs = 2
    max_inputs = 2

    def run(self, inputs: Sequence[PdfInput], params: InsertPagesParams) -> OperationResult:
        base, insert = inputs[0], inputs[1]
        ensure_pdf(base.data, base.name)
        ensure_pdf(insert.data, insert.name)
        data = pe.insert_pages_at(base.data, insert.data, params.position)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"position": params.position})


class AddBlankParams(OperationParams):
    position: int = Field(ge=0, default=0)
    count: int = Field(ge=1, default=1)
    width: float | None = None
    height: float | None = None
    output_name: str = "com-paginas-em-branco.pdf"


@register
class AddBlankOperation(PdfOperation[AddBlankParams]):
    name = "add-blank"
    category = "organizar"
    summary = "Insere páginas em branco na posição indicada."
    params_model = AddBlankParams

    def run(self, inputs: Sequence[PdfInput], params: AddBlankParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = item.data
        for i in range(params.count):
            data = pe.add_blank_page_at(
                data,
                params.position + i,
                width=params.width,
                height=params.height,
            )
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"added": params.count})


class RemoveBlankParams(OperationParams):
    threshold: float = Field(default=0.99, ge=0.0, le=1.0)
    dpi: int = Field(default=72, ge=10, le=300)
    output_name: str = "sem-paginas-em-branco.pdf"


@register
class RemoveBlankOperation(PdfOperation[RemoveBlankParams]):
    name = "remove-blank"
    category = "organizar"
    summary = "Detecta e remove páginas em branco do documento."
    params_model = RemoveBlankParams

    def run(self, inputs: Sequence[PdfInput], params: RemoveBlankParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        blank_indices = render_engine.detect_blank_pages(
            item.data, dpi=params.dpi, threshold=params.threshold
        )
        total = pe.count_pages(item.data)
        kept = [i for i in range(total) if i not in set(blank_indices)]
        if not kept:
            raise InvalidInputError("todas as páginas são em branco; nenhuma seria mantida")
        return _build(item.data, kept, params.output_name)
