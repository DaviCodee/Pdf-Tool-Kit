"""Operação: inserir números de página."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import field_validator

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import overlay
from pdftoolkit.engines import pypdf_engine as pe

# Literal vira `enum` no JSON Schema do pydantic — o hub do site renderiza
# isso como <select> automaticamente, sem hardcode no frontend.
Position = Literal[
    "top-left",
    "top-center",
    "top-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]


class PageNumbersParams(OperationParams):
    start: int = 1
    position: Position = "bottom-center"
    margin: float = 36.0
    font_size: float = 11.0
    template: str = "{n}"
    pages: str | None = None
    output_name: str = "numerado.pdf"

    @field_validator("template")
    @classmethod
    def _valid_template(cls, value: str) -> str:
        try:
            value.format(n=1, total=1)
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError("template inválido; use apenas {n} e {total}") from exc
        return value


@register
class PageNumbersOperation(PdfOperation[PageNumbersParams]):
    name = "page-numbers"
    category = "editar"
    summary = "Carimba números de página em uma posição configurável."
    params_model = PageNumbersParams

    def run(self, inputs: Sequence[PdfInput], params: PageNumbersParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        total_pages = len(writer.pages)
        targets = (
            parse_page_ranges(params.pages, total_pages, unique=True)
            if params.pages is not None
            else list(range(total_pages))
        )
        if not targets:
            raise InvalidInputError("nenhuma página selecionada")

        count = len(targets)
        for sequence, index in enumerate(targets):
            width, height = pe.page_size(reader, index)
            x, y, anchor = _place(width, height, params.position, params.margin)
            label = params.template.format(n=params.start + sequence, total=count)
            stamp = overlay.make_text_overlay(
                width,
                height,
                label,
                x=x,
                y=y,
                size=params.font_size,
                anchor=anchor,
            )
            pe.merge_overlay(writer, [index], stamp, over=True)

        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"numbered": count})


def _place(
    width: float, height: float, position: str, margin: float
) -> tuple[float, float, str]:
    vertical, _, horizontal = position.partition("-")
    if horizontal == "left":
        x, anchor = margin, "left"
    elif horizontal == "right":
        x, anchor = width - margin, "right"
    else:
        x, anchor = width / 2.0, "center"
    y = height - margin if vertical == "top" else margin
    return x, y, anchor


class BatesParams(OperationParams):
    prefix: str = ""
    suffix: str = ""
    start: int = 1
    digits: int = 6
    position: Position = "bottom-right"
    margin: float = 36.0
    font_size: float = 10.0
    pages: str | None = None
    output_name: str = "bates.pdf"


@register
class BatesOperation(PdfOperation[BatesParams]):
    name = "bates"
    category = "editar"
    summary = "Aplica numeração Bates (prefixo + número com dígitos fixos + sufixo)."
    params_model = BatesParams

    def run(self, inputs: Sequence[PdfInput], params: BatesParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        total_pages = len(writer.pages)
        targets = (
            parse_page_ranges(params.pages, total_pages, unique=True)
            if params.pages is not None
            else list(range(total_pages))
        )
        if not targets:
            raise InvalidInputError("nenhuma página selecionada")

        for sequence, index in enumerate(targets):
            width, height = pe.page_size(reader, index)
            x, y, anchor = _place(width, height, params.position, params.margin)
            number = str(params.start + sequence).zfill(params.digits)
            label = f"{params.prefix}{number}{params.suffix}"
            stamp = overlay.make_text_overlay(
                width, height, label, x=x, y=y, size=params.font_size, anchor=anchor
            )
            pe.merge_overlay(writer, [index], stamp, over=True)

        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"stamped": len(targets)})
