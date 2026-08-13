"""Operação: inserir marca d'água de texto."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import Field, field_validator

from pdftoolkit.core.errors import InvalidInputError, OperationError
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
    # Convenção única 0-100 (percentual). Slider no hub renderiza esse range.
    # Quebrou compat com a versão anterior (que aceitava ratio 0-1), mas a forma
    # ambígua causava confusão (typing 30 = 0.3 ratio = transparente, não 30%).
    opacity: float = Field(default=30.0, ge=0.0, le=100.0)
    angle: float = 45.0
    pages: str | None = None
    output_name: str = "marca-dagua.pdf"

    # Hint pro hub: opacity vira slider com chips de preset. text + font_size
    # + angle também disparam re-preview quando mudam (não só opacity).
    model_config = {
        "json_schema_extra": {
            "x-inputs": {
                "opacity": {
                    "type": "slider",
                    "label": "opacidade",
                    "help": "0 invisível · 30 sutil · 50 visível · 70 forte · 100 opaco.",
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "presets": [15, 30, 50, 70],
                    "unit": "%",
                    # IDs das outras fields que disparam re-preview quando
                    # mudam. Sem isso o preview só atualiza no slider.
                    "preview_with": ["text", "font_size", "angle"],
                },
            }
        }
    }


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
                opacity=params.opacity / 100.0,
                angle=params.angle,
            )
            pe.merge_overlay(writer, [index], stamp, over=True)

        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"stamped": len(targets)})


# ---- Preview ---------------------------------------------------------------
#
# Aplica a marca d'água na primeira página só e devolve um PNG rasterizado
# (PyMuPDF). Usado pelo hub pra mostrar preview ao vivo enquanto o user arrasta
# o slider de opacidade. Mantém os mesmos params de WatermarkParams — quando
# o toolkit adiciona um novo field, basta reusar a classe.
#
# Custo: ~150-400ms por request a 72 DPI (uma página). Bom o suficiente pra
# debounce de 300ms no cliente. Se ficar lento, baixar DPI pra 60.

class WatermarkPreviewParams(WatermarkParams):
    output_name: str = "preview.png"  # só pra satisfazer OperationParams; não é gravado
    dpi: int = 72  # 72 = rápido; hub pode pedir 90 se quiser mais detalhe


@register
class WatermarkPreviewOperation(PdfOperation[WatermarkPreviewParams]):
    name = "watermark-preview"
    category = "editar"
    summary = "Preview rasterizado (PNG) da marca d'água na primeira página — alimenta o slider do hub."
    params_model = WatermarkPreviewParams

    def run(self, inputs: Sequence[PdfInput], params: WatermarkPreviewParams) -> OperationResult:
        from pdftoolkit.engines import render as render_engine

        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        width, height = pe.page_size(reader, 0)
        stamp = overlay.make_watermark_overlay(
            width,
            height,
            params.text,
            size=params.font_size,
            opacity=params.opacity / 100.0,
            angle=params.angle,
        )
        pe.merge_overlay(writer, [0], stamp, over=True)
        preview_pdf_bytes = pe.write_bytes(writer)
        # Renderiza só a primeira página.
        pngs = render_engine.render_pages(preview_pdf_bytes, indices=[0], fmt="png", dpi=params.dpi)
        if not pngs:
            raise OperationError("renderização não devolveu bytes")
        artifact = Artifact(
            data=pngs[0],
            filename="preview.png",
            media_type="image/png",
        )
        return OperationResult(
            artifacts=[artifact],
            meta={"page": 0, "dpi": params.dpi, "bytes": len(pngs[0])},
        )


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
