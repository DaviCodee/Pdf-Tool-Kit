"""Operações de conversão entre PDF e imagens, e conversão de formato."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import ghostscript
from pdftoolkit.engines import images as images_engine
from pdftoolkit.engines import render

_MEDIA = {"png": "image/png", "jpg": "image/jpeg"}


class PdfToImageParams(OperationParams):
    format: Literal["png", "jpg"] = "png"
    dpi: int = Field(default=150, ge=10, le=600)
    pages: str | None = None
    password: str | None = None
    output_stem: str = "pagina"


@register
class PdfToImageOperation(PdfOperation[PdfToImageParams]):
    name = "pdf-to-image"
    category = "converter"
    summary = "Rasteriza páginas do PDF para imagens PNG ou JPG."
    params_model = PdfToImageParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToImageParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        total = render.page_count(item.data, params.password)
        indices = (
            parse_page_ranges(params.pages, total, unique=True)
            if params.pages is not None
            else list(range(total))
        )
        rendered = render.render_pages(
            item.data, indices, dpi=params.dpi, fmt=params.format, password=params.password
        )
        stem = safe_filename(params.output_stem, fallback="pagina").removesuffix(".pdf")
        artifacts = [
            Artifact(
                data=image,
                filename=f"{stem}-{indices[position] + 1:03d}.{params.format}",
                media_type=_MEDIA[params.format],
            )
            for position, image in enumerate(rendered)
        ]
        return OperationResult(artifacts=artifacts, meta={"images": len(artifacts)})


class ThumbnailParams(OperationParams):
    width: int = Field(default=256, ge=16, le=2000)
    pages: str | None = None
    password: str | None = None
    output_stem: str = "miniatura"


@register
class ThumbnailOperation(PdfOperation[ThumbnailParams]):
    name = "thumbnail"
    category = "converter"
    summary = "Gera miniaturas PNG (por padrão da primeira página)."
    params_model = ThumbnailParams

    def run(self, inputs: Sequence[PdfInput], params: ThumbnailParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        if params.pages is not None:
            total = render.page_count(item.data, params.password)
            indices = parse_page_ranges(params.pages, total, unique=True)
        else:
            indices = [0]
        rendered = render.thumbnails(
            item.data, indices, width=params.width, password=params.password
        )
        stem = safe_filename(params.output_stem, fallback="miniatura").removesuffix(".pdf")
        artifacts = [
            Artifact(
                data=image,
                filename=f"{stem}-{indices[position] + 1:03d}.png",
                media_type="image/png",
            )
            for position, image in enumerate(rendered)
        ]
        return OperationResult(artifacts=artifacts, meta={"thumbnails": len(artifacts)})


class ImagesToPdfParams(OperationParams):
    dpi: int = Field(default=150, ge=10, le=600)
    output_name: str = "imagens.pdf"


@register
class ImagesToPdfOperation(PdfOperation[ImagesToPdfParams]):
    name = "images-to-pdf"
    category = "converter"
    summary = "Combina imagens (PNG/JPG) em um único PDF, uma por página."
    params_model = ImagesToPdfParams
    min_inputs = 1
    max_inputs = None

    def run(self, inputs: Sequence[PdfInput], params: ImagesToPdfParams) -> OperationResult:
        data = images_engine.images_to_pdf([item.data for item in inputs], dpi=params.dpi)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pages": len(inputs)})


class ToPdfAParams(OperationParams):
    level: Literal[1, 2, 3] = 2
    output_name: str = "arquivo-pdfa.pdf"


@register
class ToPdfAOperation(PdfOperation[ToPdfAParams]):
    name = "to-pdfa"
    category = "converter"
    summary = "Converte um PDF para o formato PDF/A (arquivo de longa duração)."
    params_model = ToPdfAParams

    def run(self, inputs: Sequence[PdfInput], params: ToPdfAParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = ghostscript.to_pdfa(item.data, level=params.level)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pdfa_level": params.level})


class RepairParams(OperationParams):
    output_name: str = "reparado.pdf"


@register
class RepairOperation(PdfOperation[RepairParams]):
    name = "repair"
    category = "converter"
    summary = "Tenta reparar um PDF corrompido regravando-o via Ghostscript."
    params_model = RepairParams

    def run(self, inputs: Sequence[PdfInput], params: RepairParams) -> OperationResult:
        item = inputs[0]
        data = ghostscript.repair(item.data)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"repaired": True})
