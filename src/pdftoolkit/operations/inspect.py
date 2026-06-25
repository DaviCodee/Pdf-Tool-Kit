"""Operações de inspeção: validar, listar fontes e inspecionar estrutura."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf
from pdftoolkit.engines import pikepdf_engine as pike


class ValidateParams(OperationParams):
    pass


@register
class ValidateOperation(PdfOperation[ValidateParams]):
    name = "validate"
    category = "info"
    summary = "Verifica a integridade estrutural do PDF e reporta problemas encontrados."
    params_model = ValidateParams

    def run(self, inputs: Sequence[PdfInput], params: ValidateParams) -> OperationResult:
        item = inputs[0]
        result = pike.validate_pdf(item.data)
        return OperationResult(artifacts=[], meta=result)


class FontListParams(OperationParams):
    pass


@register
class FontListOperation(PdfOperation[FontListParams]):
    name = "font-list"
    category = "info"
    summary = "Lista todas as fontes referenciadas no documento."
    params_model = FontListParams

    def run(self, inputs: Sequence[PdfInput], params: FontListParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        fonts = pike.list_fonts(item.data)
        return OperationResult(artifacts=[], meta={"fonts": fonts, "count": len(fonts)})


class HeadersParams(OperationParams):
    pass


@register
class HeadersOperation(PdfOperation[HeadersParams]):
    name = "headers"
    category = "info"
    summary = "Retorna informações estruturais do PDF: versão, tamanho de páginas, formulários, etc."
    params_model = HeadersParams

    def run(self, inputs: Sequence[PdfInput], params: HeadersParams) -> OperationResult:
        item = inputs[0]
        info = pike.get_info(item.data)
        return OperationResult(artifacts=[], meta=info)
