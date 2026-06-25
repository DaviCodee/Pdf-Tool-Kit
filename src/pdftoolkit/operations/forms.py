"""Operações de formulário: ler e preencher campos."""

from __future__ import annotations

from collections.abc import Sequence

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pikepdf_engine as pike
from pdftoolkit.engines import pypdf_engine as pe


class FormReadParams(OperationParams):
    pass


@register
class FormReadOperation(PdfOperation[FormReadParams]):
    name = "form-read"
    category = "info"
    summary = "Lista os campos de formulário e seus valores atuais."
    params_model = FormReadParams

    def run(self, inputs: Sequence[PdfInput], params: FormReadParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        fields = pe.read_form_fields(item.data)
        return OperationResult(artifacts=[], meta={"fields": fields})


class FormFillParams(OperationParams):
    values: dict[str, str]
    output_name: str = "formulario.pdf"


@register
class FormFillOperation(PdfOperation[FormFillParams]):
    name = "form-fill"
    category = "editar"
    summary = "Preenche campos de formulário com os valores informados."
    params_model = FormFillParams

    def run(self, inputs: Sequence[PdfInput], params: FormFillParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = pe.fill_form(item.data, params.values)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"filled": sorted(params.values)})


class FillFlattenParams(OperationParams):
    values: dict[str, str]
    output_name: str = "formulario-fixo.pdf"


@register
class FillFlattenOperation(PdfOperation[FillFlattenParams]):
    name = "fill-flatten"
    category = "editar"
    summary = "Preenche os campos do formulário e os achata (torna não editáveis)."
    params_model = FillFlattenParams

    def run(self, inputs: Sequence[PdfInput], params: FillFlattenParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        filled = pe.fill_form(item.data, params.values)
        data = pike.flatten_annotations(filled)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(
            artifacts=[artifact], meta={"filled": sorted(params.values), "flattened": True}
        )


class FlattenParams(OperationParams):
    output_name: str = "achatado.pdf"


@register
class FlattenOperation(PdfOperation[FlattenParams]):
    name = "flatten"
    category = "editar"
    summary = "Achata todas as anotações interativas (formulários, widgets, etc.)."
    params_model = FlattenParams

    def run(self, inputs: Sequence[PdfInput], params: FlattenParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        data = pike.flatten_annotations(item.data)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"flattened": True})
