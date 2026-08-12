"""Operação: inserir marca d'água de texto."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

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
from pdftoolkit.engines import qr as qr_engine


# Anchor vira enum no JSON Schema → <select> no hub.
Anchor = Literal["left", "center", "right"]


class AddTextParams(OperationParams):
    text: str = Field(min_length=1)
    x: float = 0.0
    y: float = 0.0
    font_size: float = 12.0
    anchor: Anchor = "left"
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0)
    pages: str | None = None
    output_name: str = "com-texto.pdf"


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


@register
class AddTextOperation(PdfOperation[AddTextParams]):
    name = "add-text"
    category = "editar"
    summary = "Insere texto em posição absoluta (em pontos) nas páginas indicadas."
    params_model = AddTextParams

    def run(self, inputs: Sequence[PdfInput], params: AddTextParams) -> OperationResult:
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
            stamp = overlay.make_text_overlay(
                width, height, params.text,
                x=params.x, y=params.y,
                size=params.font_size,
                anchor=params.anchor,
                rgb=params.rgb,
            )
            pe.merge_overlay(writer, [index], stamp, over=True)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pages": len(targets)})


class StampParams(OperationParams):
    pages: str | None = None
    output_name: str = "carimbado.pdf"


@register
class StampOperation(PdfOperation[StampParams]):
    name = "stamp"
    category = "editar"
    summary = "Aplica a primeira página do segundo PDF como carimbo (por cima) nas páginas alvo."
    params_model = StampParams
    min_inputs = 2
    max_inputs = 2

    def run(self, inputs: Sequence[PdfInput], params: StampParams) -> OperationResult:
        base, stamp_pdf = inputs[0], inputs[1]
        ensure_pdf(base.data, base.name)
        ensure_pdf(stamp_pdf.data, stamp_pdf.name)
        reader = pe.open_reader(base.data)
        writer = pe.clone_writer(reader)
        total = len(writer.pages)
        targets = (
            parse_page_ranges(params.pages, total, unique=True)
            if params.pages is not None
            else list(range(total))
        )
        if not targets:
            raise InvalidInputError("nenhuma página selecionada")
        pe.merge_overlay(writer, targets, stamp_pdf.data, over=True)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"stamped": len(targets)})


class PdfOverlayParams(OperationParams):
    under: bool = False
    pages: str | None = None
    output_name: str = "overlay.pdf"


@register
class PdfOverlayOperation(PdfOperation[PdfOverlayParams]):
    name = "overlay"
    category = "editar"
    summary = "Compõe a primeira página do segundo PDF sobre (ou sob) as páginas do primeiro."
    params_model = PdfOverlayParams
    min_inputs = 2
    max_inputs = 2

    def run(self, inputs: Sequence[PdfInput], params: PdfOverlayParams) -> OperationResult:
        base, over_pdf = inputs[0], inputs[1]
        ensure_pdf(base.data, base.name)
        ensure_pdf(over_pdf.data, over_pdf.name)
        reader = pe.open_reader(base.data)
        writer = pe.clone_writer(reader)
        total = len(writer.pages)
        targets = (
            parse_page_ranges(params.pages, total, unique=True)
            if params.pages is not None
            else list(range(total))
        )
        if not targets:
            raise InvalidInputError("nenhuma página selecionada")
        pe.merge_overlay(writer, targets, over_pdf.data, over=not params.under)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"composed": len(targets)})


class AddImageParams(OperationParams):
    x: float = 0.0
    y: float = 0.0
    width: float | None = None
    height: float | None = None
    pages: str | None = None
    output_name: str = "com-imagem.pdf"


@register
class AddImageOperation(PdfOperation[AddImageParams]):
    name = "add-image"
    category = "editar"
    summary = "Insere uma imagem (PNG/JPG) em posição absoluta nas páginas indicadas."
    params_model = AddImageParams
    min_inputs = 2
    max_inputs = 2

    def run(self, inputs: Sequence[PdfInput], params: AddImageParams) -> OperationResult:
        base, img_input = inputs[0], inputs[1]
        ensure_pdf(base.data, base.name)
        reader = pe.open_reader(base.data)
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
            stamp = overlay.make_image_overlay(
                width, height, img_input.data,
                x=params.x, y=params.y,
                img_width=params.width,
                img_height=params.height,
            )
            pe.merge_overlay(writer, [index], stamp, over=True)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"pages": len(targets)})


class QrEmbedParams(OperationParams):
    content: str = Field(min_length=1)
    x: float = 0.0
    y: float = 0.0
    size: float = Field(default=100.0, gt=0)
    pages: str | None = None
    output_name: str = "com-qr.pdf"


@register
class QrEmbedOperation(PdfOperation[QrEmbedParams]):
    name = "qr-embed"
    category = "editar"
    summary = "Gera um QR code a partir de 'content' e o embute nas páginas indicadas."
    params_model = QrEmbedParams

    def run(self, inputs: Sequence[PdfInput], params: QrEmbedParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        qr_png = qr_engine.make_qr_png(params.content)
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
            stamp = overlay.make_image_overlay(
                width, height, qr_png,
                x=params.x, y=params.y,
                img_width=params.size,
                img_height=params.size,
            )
            pe.merge_overlay(writer, [index], stamp, over=True)
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(
            artifacts=[artifact], meta={"content": params.content, "pages": len(targets)}
        )
