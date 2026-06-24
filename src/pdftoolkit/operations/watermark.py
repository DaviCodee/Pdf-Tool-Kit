"""Operação: inserir marca d'água de texto."""

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
from pdftoolkit.engines import overlay
from pdftoolkit.engines import pypdf_engine as pe


class WatermarkParams(OperationParams):
    text: str = Field(min_length=1)
    font_size: float = 48.0
    opacity: float = Field(default=0.15, ge=0.0, le=1.0)
    angle: float = 45.0
    pages: str | None = None
    output_name: str = "marca-dagua.pdf"


@register
class WatermarkOperation(PdfOperation[WatermarkParams]):
    name = "watermark"
    category = "editar"
    summary = "Aplica uma marca d'água de texto diagonal sobre as páginas."
    params_model = WatermarkParams

    def run(self, inputs: Sequence[PdfInput], params: WatermarkParams) -> OperationResult:
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

        for index in targets:
            width, height = pe.page_size(reader, index)
            stamp = overlay.make_watermark_overlay(
                width,
                height,
                params.text,
                size=params.font_size,
                opacity=params.opacity,
                angle=params.angle,
            )
            pe.merge_overlay(writer, [index], stamp, over=True)

        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"stamped": len(targets)})
