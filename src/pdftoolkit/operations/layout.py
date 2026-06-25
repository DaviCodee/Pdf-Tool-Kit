"""Operações de layout de página: alterar tamanho."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.ranges import parse_page_ranges
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe

# Tamanhos predefinidos em pontos (72 pt = 1 polegada).
_PRESETS: dict[str, tuple[float, float]] = {
    "a4": (595.28, 841.89),
    "a3": (841.89, 1190.55),
    "a5": (419.53, 595.28),
    "letter": (612.0, 792.0),
    "legal": (612.0, 1008.0),
    "tabloid": (792.0, 1224.0),
}


class PageSizeParams(OperationParams):
    preset: str | None = None
    width: float | None = Field(default=None, gt=0)
    height: float | None = Field(default=None, gt=0)
    pages: str | None = None
    output_name: str = "redimensionado.pdf"

    def model_post_init(self, __context) -> None:
        if self.preset is None and (self.width is None or self.height is None):
            raise ValueError("informe 'preset' ou ambos 'width' e 'height'")
        if self.preset is not None and self.preset.lower() not in _PRESETS:
            raise ValueError(f"preset inválido; opções: {sorted(_PRESETS)}")


@register
class PageSizeOperation(PdfOperation[PageSizeParams]):
    name = "page-size"
    category = "editar"
    summary = "Altera o tamanho das páginas para um preset (a4, letter…) ou dimensões em pontos."
    params_model = PageSizeParams

    def run(self, inputs: Sequence[PdfInput], params: PageSizeParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        if params.preset is not None:
            width, height = _PRESETS[params.preset.lower()]
        else:
            assert params.width is not None and params.height is not None
            width, height = params.width, params.height

        reader = pe.open_reader(item.data)
        total = len(reader.pages)
        indices = (
            parse_page_ranges(params.pages, total, unique=True)
            if params.pages is not None
            else None
        )
        data = pe.resize_pages(item.data, width, height, indices)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(
            artifacts=[artifact],
            meta={"width": width, "height": height, "pages": total},
        )
