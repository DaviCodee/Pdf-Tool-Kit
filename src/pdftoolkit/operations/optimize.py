"""Operações de otimização: comprimir e linearizar para web."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import ghostscript
from pdftoolkit.engines import pikepdf_engine as pike


class CompressParams(OperationParams):
    quality: Literal["screen", "ebook", "printer", "prepress"] = "ebook"
    output_name: str = "comprimido.pdf"


@register
class CompressOperation(PdfOperation[CompressParams]):
    name = "compress"
    category = "otimizar"
    summary = "Reduz o tamanho do PDF recomprimindo imagens (Ghostscript)."
    params_model = CompressParams

    def run(self, inputs: Sequence[PdfInput], params: CompressParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = ghostscript.compress(item.data, params.quality)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(
            artifacts=[artifact],
            meta={"original_bytes": len(item.data), "result_bytes": len(data)},
        )


class OptimizeWebParams(OperationParams):
    output_name: str = "otimizado.pdf"


@register
class OptimizeWebOperation(PdfOperation[OptimizeWebParams]):
    name = "optimize-web"
    category = "otimizar"
    summary = "Lineariza o PDF para carregamento progressivo na web."
    params_model = OptimizeWebParams

    def run(self, inputs: Sequence[PdfInput], params: OptimizeWebParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = pike.linearize(item.data)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"linearized": True})
