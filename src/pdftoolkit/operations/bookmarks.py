"""Operações de marcadores (bookmarks / outline)."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pikepdf_engine as pike


class ListBookmarksParams(OperationParams):
    pass


@register
class ListBookmarksOperation(PdfOperation[ListBookmarksParams]):
    name = "list-bookmarks"
    category = "info"
    summary = "Lista os marcadores (outline) do documento como árvore JSON."
    params_model = ListBookmarksParams

    def run(self, inputs: Sequence[PdfInput], params: ListBookmarksParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        bookmarks = pike.list_bookmarks(item.data)
        return OperationResult(artifacts=[], meta={"bookmarks": bookmarks, "count": len(bookmarks)})


class BookmarkEntry(OperationParams):
    title: str
    page: int = 0


class AddBookmarksParams(OperationParams):
    bookmarks: list[BookmarkEntry]
    output_name: str = "com-marcadores.pdf"


@register
class AddBookmarksOperation(PdfOperation[AddBookmarksParams]):
    name = "bookmark"
    category = "editar"
    summary = "Adiciona marcadores ao PDF. Cada entrada precisa de 'title' e 'page' (0-indexed)."
    params_model = AddBookmarksParams

    def run(self, inputs: Sequence[PdfInput], params: AddBookmarksParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        entries = [bm.model_dump() for bm in params.bookmarks]
        data = pike.add_bookmarks(item.data, entries)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"added": len(entries)})
