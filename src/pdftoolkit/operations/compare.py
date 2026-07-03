"""Operações: comparar dois PDFs por texto (diff unificado) ou visualmente."""

from __future__ import annotations

import difflib
from collections.abc import Sequence

from pydantic import Field

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pypdf_engine as pe
from pdftoolkit.engines import render


class CompareParams(OperationParams):
    output_name: str = "diferencas.diff"


@register
class CompareOperation(PdfOperation[CompareParams]):
    name = "compare"
    category = "info"
    summary = "Compara o texto de dois PDFs e gera um diff unificado."
    params_model = CompareParams
    min_inputs = 2
    max_inputs = 2

    def run(self, inputs: Sequence[PdfInput], params: CompareParams) -> OperationResult:
        first, second = inputs[0], inputs[1]
        ensure_pdf(first.data, first.name)
        ensure_pdf(second.data, second.name)

        text_a = "\n".join(pe.extract_page_texts(first.data)).splitlines()
        text_b = "\n".join(pe.extract_page_texts(second.data)).splitlines()
        diff = list(
            difflib.unified_diff(
                text_a, text_b, fromfile=first.name, tofile=second.name, lineterm=""
            )
        )
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

        artifact = Artifact(
            data="\n".join(diff).encode("utf-8"),
            filename=safe_filename(params.output_name, fallback="diferencas.diff"),
            media_type="text/plain",
        )
        return OperationResult(
            artifacts=[artifact],
            meta={"added": added, "removed": removed, "identical": not diff},
        )


class CompareVisualParams(OperationParams):
    dpi: int = Field(default=120, ge=36, le=300)
    output_name: str = "comparacao.pdf"


@register
class CompareVisualOperation(PdfOperation[CompareVisualParams]):
    name = "compare-visual"
    category = "info"
    summary = (
        "Compara dois PDFs pixel a pixel e gera um PDF com as regiões "
        "divergentes contornadas em vermelho (extras 'render' e 'images')."
    )
    params_model = CompareVisualParams
    min_inputs = 2
    max_inputs = 2

    def run(self, inputs: Sequence[PdfInput], params: CompareVisualParams) -> OperationResult:
        first, second = inputs[0], inputs[1]
        ensure_pdf(first.data, first.name)
        ensure_pdf(second.data, second.name)
        data, has_diff = render.compare_visual(first.data, second.data, dpi=params.dpi)
        artifact = Artifact(
            data=data,
            filename=safe_filename(params.output_name, fallback="comparacao.pdf"),
        )
        return OperationResult(artifacts=[artifact], meta={"has_diff": has_diff})
