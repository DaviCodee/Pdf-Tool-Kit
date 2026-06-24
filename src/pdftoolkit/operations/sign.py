"""Operação: assinar digitalmente um PDF."""

from __future__ import annotations

import base64
import binascii
from collections.abc import Sequence

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import sign as sign_engine


class SignParams(OperationParams):
    pkcs12_base64: str | None = None
    passphrase: str | None = None
    field_name: str = "Signature1"
    reason: str | None = None
    location: str | None = None
    ephemeral: bool = False
    output_name: str = "assinado.pdf"


@register
class SignOperation(PdfOperation[SignParams]):
    name = "sign"
    category = "seguranca"
    summary = "Assina digitalmente um PDF (certificado .pfx ou um efêmero de teste)."
    params_model = SignParams

    def run(self, inputs: Sequence[PdfInput], params: SignParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        pkcs12_data = None
        if params.pkcs12_base64 is not None:
            try:
                pkcs12_data = base64.b64decode(params.pkcs12_base64, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise InvalidInputError("pkcs12_base64 não é base64 válido") from exc
        data = sign_engine.sign(
            item.data,
            pkcs12_data=pkcs12_data,
            passphrase=params.passphrase,
            field_name=params.field_name,
            reason=params.reason,
            location=params.location,
            ephemeral=params.ephemeral,
        )
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"field": params.field_name})
