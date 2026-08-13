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
from pdftoolkit.engines import ghostscript, render
from pdftoolkit.engines import html_to_pdf as html_engine
from pdftoolkit.engines import images as images_engine
from pdftoolkit.engines import tables as tables_engine
from pdftoolkit.engines import text as text_engine
from pdftoolkit.engines import txt_to_pdf as txt_engine
from pdftoolkit.engines import xlsx as xlsx_engine

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
    """Combina imagens (PNG/JPG) em um único PDF, uma por página.

    O campo `dpi` aceita presets 72/150/300/600 (front-end renderiza chips).
    Maior dpi = mais pixels por página = arquivo maior + menos zoom no reader.
    """

    dpi: int = Field(default=150, ge=10, le=600)
    output_name: str = "imagens.pdf"

    model_config = {
        "json_schema_extra": {
            "x-inputs": {
                "dpi": {
                    "type": "number_with_presets",
                    "presets": [72, 150, 300, 600],
                    "label": "dpi (qualidade)",
                    "help": "maior dpi = mais pixels = menos zoom no reader.",
                    "unit": "dpi",
                },
            }
        }
    }


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


# ---------------------------------------------------------------------------
# PDF -> texto / estrutura
# ---------------------------------------------------------------------------


class PdfToTextParams(OperationParams):
    pages: str | None = None
    password: str | None = None
    output_name: str = "texto.txt"


@register
class PdfToTextOperation(PdfOperation[PdfToTextParams]):
    name = "pdf-to-text"
    category = "converter"
    summary = "Extrai o texto de cada página em um único arquivo .txt."
    params_model = PdfToTextParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToTextParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        all_pages = text_engine.extract_pages_text(item.data, params.password)
        if params.pages is not None:
            indices = parse_page_ranges(params.pages, len(all_pages), unique=True)
            pages = [all_pages[index] for index in indices]
        else:
            pages = all_pages
        body = "\n\n".join(pages)
        artifact = Artifact(
            data=body.encode("utf-8"),
            filename=safe_filename(params.output_name, fallback="texto.txt"),
            media_type="text/plain",
        )
        return OperationResult(artifacts=[artifact], meta={"pages": len(pages)})


class PdfToJsonParams(OperationParams):
    password: str | None = None
    output_name: str = "layout.json"


@register
class PdfToJsonOperation(PdfOperation[PdfToJsonParams]):
    name = "pdf-to-json"
    category = "converter"
    summary = (
        "Extrai o texto de cada página em JSON com bounding boxes aproximadas "
        "(requer extra 'tables' para o parser de layout)."
    )
    params_model = PdfToJsonParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToJsonParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        pages = text_engine.extract_pages_layout(item.data, params.password)
        data = text_engine.layout_to_json(pages)
        artifact = Artifact(
            data=data,
            filename=safe_filename(params.output_name, fallback="layout.json"),
            media_type="application/json",
        )
        return OperationResult(artifacts=[artifact], meta={"pages": len(pages)})


class PdfToHtmlParams(OperationParams):
    password: str | None = None
    output_name: str = "documento.html"


@register
class PdfToHtmlOperation(PdfOperation[PdfToHtmlParams]):
    name = "pdf-to-html"
    category = "converter"
    summary = "Empacota o texto do PDF em um documento HTML simples e autocontido."
    params_model = PdfToHtmlParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToHtmlParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        html = text_engine.pages_to_html(item.data, params.password)
        artifact = Artifact(
            data=html.encode("utf-8"),
            filename=safe_filename(params.output_name, fallback="documento.html"),
            media_type="text/html",
        )
        return OperationResult(artifacts=[artifact], meta={"bytes": len(html.encode("utf-8"))})


class PdfToMarkdownParams(OperationParams):
    password: str | None = None
    output_name: str = "documento.md"


@register
class PdfToMarkdownOperation(PdfOperation[PdfToMarkdownParams]):
    name = "pdf-to-markdown"
    category = "converter"
    summary = (
        "Converte o PDF em Markdown, inferindo cabeçalhos pelo tamanho da fonte "
        "(requer extra 'tables')."
    )
    params_model = PdfToMarkdownParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToMarkdownParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        text = text_engine.pages_to_markdown(item.data, params.password)
        artifact = Artifact(
            data=text.encode("utf-8"),
            filename=safe_filename(params.output_name, fallback="documento.md"),
            media_type="text/markdown",
        )
        return OperationResult(artifacts=[artifact], meta={"chars": len(text)})


# ---------------------------------------------------------------------------
# PDF -> imagens (formatos extras via Pillow)
# ---------------------------------------------------------------------------


def _render_via_pillow(
    data: bytes,
    password: str | None,
    pages: str | None,
    dpi: int,
    target: str,
    stem: str,
    extra_quality: int | None = None,
    lossless: bool = False,
) -> list[Artifact]:
    total = render.page_count(data, password)
    indices = (
        parse_page_ranges(pages, total, unique=True) if pages is not None else list(range(total))
    )
    pngs = render.render_pages(data, indices, dpi=dpi, fmt="png", password=password)
    artifacts: list[Artifact] = []
    for position, png in enumerate(pngs):
        converted = images_engine.convert_image(
            png, target, quality=extra_quality, lossless=lossless
        )
        ext = "tif" if target == "tiff" else target
        media = _PIL_MEDIA.get(target, "application/octet-stream")
        artifacts.append(
            Artifact(
                data=converted,
                filename=f"{stem}-{indices[position] + 1:03d}.{ext}",
                media_type=media,
            )
        )
    return artifacts


_PIL_MEDIA = {
    "tiff": "image/tiff",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "ppm": "image/x-portable-pixmap",
}


class PdfToTiffParams(OperationParams):
    dpi: int = Field(default=150, ge=10, le=600)
    pages: str | None = None
    password: str | None = None
    output_stem: str = "pagina"


@register
class PdfToTiffOperation(PdfOperation[PdfToTiffParams]):
    name = "pdf-to-tiff"
    category = "converter"
    summary = "Rasteriza páginas para TIFF (extras 'render' + 'images')."
    params_model = PdfToTiffParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToTiffParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        stem = safe_filename(params.output_stem, fallback="pagina").removesuffix(".pdf")
        artifacts = _render_via_pillow(
            item.data, params.password, params.pages, params.dpi, "tiff", stem
        )
        return OperationResult(artifacts=artifacts, meta={"images": len(artifacts)})


class PdfToWebPParams(OperationParams):
    dpi: int = Field(default=150, ge=10, le=600)
    quality: int = Field(default=80, ge=1, le=100)
    lossless: bool = False
    pages: str | None = None
    password: str | None = None
    output_stem: str = "pagina"


@register
class PdfToWebPOperation(PdfOperation[PdfToWebPParams]):
    name = "pdf-to-webp"
    category = "converter"
    summary = "Rasteriza páginas para WebP com qualidade configurável (extras 'render' + 'images')."
    params_model = PdfToWebPParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToWebPParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        stem = safe_filename(params.output_stem, fallback="pagina").removesuffix(".pdf")
        artifacts = _render_via_pillow(
            item.data,
            params.password,
            params.pages,
            params.dpi,
            "webp",
            stem,
            extra_quality=params.quality,
            lossless=params.lossless,
        )
        return OperationResult(artifacts=artifacts, meta={"images": len(artifacts)})


class PdfToBmpParams(OperationParams):
    dpi: int = Field(default=150, ge=10, le=600)
    pages: str | None = None
    password: str | None = None
    output_stem: str = "pagina"


@register
class PdfToBmpOperation(PdfOperation[PdfToBmpParams]):
    name = "pdf-to-bmp"
    category = "converter"
    summary = "Rasteriza páginas para BMP (extras 'render' + 'images')."
    params_model = PdfToBmpParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToBmpParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        stem = safe_filename(params.output_stem, fallback="pagina").removesuffix(".pdf")
        artifacts = _render_via_pillow(
            item.data, params.password, params.pages, params.dpi, "bmp", stem
        )
        return OperationResult(artifacts=artifacts, meta={"images": len(artifacts)})


class PdfToPpmParams(OperationParams):
    dpi: int = Field(default=150, ge=10, le=600)
    pages: str | None = None
    password: str | None = None
    output_stem: str = "pagina"


@register
class PdfToPpmOperation(PdfOperation[PdfToPpmParams]):
    name = "pdf-to-ppm"
    category = "converter"
    summary = "Rasteriza páginas para PPM via PyMuPDF (extra 'render', sem Pillow)."
    params_model = PdfToPpmParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToPpmParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        total = render.page_count(item.data, params.password)
        indices = (
            parse_page_ranges(params.pages, total, unique=True)
            if params.pages is not None
            else list(range(total))
        )
        # PyMuPDF exporta PPM nativamente; sem precisar de Pillow.
        ppm_bytes = render.render_pages(
            item.data, indices, dpi=params.dpi, fmt="ppm", password=params.password
        )
        stem = safe_filename(params.output_stem, fallback="pagina").removesuffix(".pdf")
        artifacts = [
            Artifact(
                data=data,
                filename=f"{stem}-{indices[position] + 1:03d}.ppm",
                media_type="image/x-portable-pixmap",
            )
            for position, data in enumerate(ppm_bytes)
        ]
        return OperationResult(artifacts=artifacts, meta={"images": len(artifacts)})


class PdfToSvgParams(OperationParams):
    pages: str | None = None
    password: str | None = None
    output_stem: str = "pagina"


@register
class PdfToSvgOperation(PdfOperation[PdfToSvgParams]):
    name = "pdf-to-svg"
    category = "converter"
    summary = "Exporta páginas como SVG vetorial (extra 'render')."
    params_model = PdfToSvgParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToSvgParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        total = render.page_count(item.data, params.password)
        indices = (
            parse_page_ranges(params.pages, total, unique=True)
            if params.pages is not None
            else list(range(total))
        )
        svgs = render.page_to_svg(item.data, indices, password=params.password)
        stem = safe_filename(params.output_stem, fallback="pagina").removesuffix(".pdf")
        artifacts = [
            Artifact(
                data=svg,
                filename=f"{stem}-{indices[position] + 1:03d}.svg",
                media_type="image/svg+xml",
            )
            for position, svg in enumerate(svgs)
        ]
        return OperationResult(artifacts=artifacts, meta={"images": len(artifacts)})


# ---------------------------------------------------------------------------
# PDF -> planilha
# ---------------------------------------------------------------------------


class PdfToXlsxParams(OperationParams):
    password: str | None = None
    output_name: str = "tabelas.xlsx"


@register
class PdfToXlsxOperation(PdfOperation[PdfToXlsxParams]):
    name = "pdf-to-xlsx"
    category = "converter"
    summary = (
        "Detecta tabelas no PDF e exporta cada uma em uma aba de um único .xlsx "
        "(extras 'tables' + 'xlsx')."
    )
    params_model = PdfToXlsxParams

    def run(self, inputs: Sequence[PdfInput], params: PdfToXlsxParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        tables = tables_engine.extract_tables(item.data)
        data = xlsx_engine.tables_to_xlsx(tables)
        artifact = Artifact(
            data=data,
            filename=safe_filename(params.output_name, fallback="tabelas.xlsx"),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        return OperationResult(artifacts=[artifact], meta={"tables": len(tables)})


# ---------------------------------------------------------------------------
# Texto / HTML -> PDF
# ---------------------------------------------------------------------------


class TxtToPdfParams(OperationParams):
    font_size: float = Field(default=11.0, ge=6.0, le=48.0)
    page_size: Literal["a4", "letter", "legal"] = "a4"
    output_name: str = "documento.pdf"


@register
class TxtToPdfOperation(PdfOperation[TxtToPdfParams]):
    name = "txt-to-pdf"
    category = "converter"
    summary = "Converte texto plano em PDF via reportlab."
    params_model = TxtToPdfParams
    min_inputs = 1
    max_inputs = None

    def run(self, inputs: Sequence[PdfInput], params: TxtToPdfParams) -> OperationResult:
        # Concatena os arquivos de texto, separados por linha em branco.
        text = "\n\n".join(item.data.decode("utf-8", errors="replace") for item in inputs)
        data = txt_engine.txt_to_pdf(text, font_size=params.font_size, page_size=params.page_size)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"chars": len(text)})


class HtmlToPdfParams(OperationParams):
    output_name: str = "documento.pdf"


@register
class HtmlToPdfOperation(PdfOperation[HtmlToPdfParams]):
    name = "html-to-pdf"
    category = "converter"
    summary = "Renderiza HTML em PDF via WeasyPrint (extra 'html' + libs nativas)."
    params_model = HtmlToPdfParams
    min_inputs = 1
    max_inputs = None

    def run(self, inputs: Sequence[PdfInput], params: HtmlToPdfParams) -> OperationResult:
        item = inputs[0]
        html = item.data.decode("utf-8", errors="replace")
        data = html_engine.html_to_pdf(html)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"bytes": len(html.encode("utf-8"))})
