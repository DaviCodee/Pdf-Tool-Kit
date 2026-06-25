"""Operação: redação real (remoção de conteúdo)."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import model_validator

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import redact as redact_engine


class RedactParams(OperationParams):
    terms: list[str] | None = None
    pattern: str | None = None
    output_name: str = "redigido.pdf"

    @model_validator(mode="after")
    def _exactly_one(self) -> RedactParams:
        if bool(self.terms) == bool(self.pattern):
            raise ValueError("informe 'terms' OU 'pattern' (exatamente um)")
        return self


@register
class RedactOperation(PdfOperation[RedactParams]):
    name = "redact"
    category = "seguranca"
    summary = "Remove definitivamente texto por termos literais ou por expressão regular."
    params_model = RedactParams

    def run(self, inputs: Sequence[PdfInput], params: RedactParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        if params.terms:
            data, count = redact_engine.redact_terms(item.data, params.terms)
        else:
            assert params.pattern is not None
            data, count = redact_engine.redact_regex(item.data, params.pattern)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"redacted": count})


class RedactRegexParams(OperationParams):
    pattern: str
    output_name: str = "redigido.pdf"


@register
class RedactRegexOperation(PdfOperation[RedactRegexParams]):
    name = "redact-regex"
    category = "seguranca"
    summary = "Remove definitivamente todas as ocorrências de um padrão regex."
    params_model = RedactRegexParams

    def run(self, inputs: Sequence[PdfInput], params: RedactRegexParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data, count = redact_engine.redact_regex(item.data, params.pattern)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"redacted": count})
