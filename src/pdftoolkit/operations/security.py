"""Operações de segurança: proteger (criptografar) e desbloquear."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field

from pdftoolkit.core.io import Artifact, OperationResult, PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.params import OperationParams
from pdftoolkit.core.registry import register
from pdftoolkit.core.validation import ensure_pdf, safe_filename
from pdftoolkit.engines import pikepdf_engine as pike
from pdftoolkit.engines import pypdf_engine as pe


class ProtectParams(OperationParams):
    user_password: str = Field(min_length=1)
    owner_password: str | None = None
    allow_printing: bool = True
    allow_copy: bool = True
    allow_modify: bool = False
    allow_annotate: bool = False
    output_name: str = "protegido.pdf"


@register
class ProtectOperation(PdfOperation[ProtectParams]):
    name = "protect"
    category = "seguranca"
    summary = "Adiciona senha e permissões (AES-256) a um PDF."
    params_model = ProtectParams

    def run(self, inputs: Sequence[PdfInput], params: ProtectParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        reader = pe.open_reader(item.data)
        writer = pe.clone_writer(reader)
        pe.encrypt(
            writer,
            user_password=params.user_password,
            owner_password=params.owner_password,
            allow_printing=params.allow_printing,
            allow_copy=params.allow_copy,
            allow_modify=params.allow_modify,
            allow_annotate=params.allow_annotate,
        )
        data = pe.write_bytes(writer)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"encrypted": True})


class UnlockParams(OperationParams):
    password: str | None = None
    output_name: str = "desbloqueado.pdf"


@register
class UnlockOperation(PdfOperation[UnlockParams]):
    name = "unlock"
    category = "seguranca"
    summary = "Remove a proteção de um PDF (requer a senha quando houver senha de usuário)."
    params_model = UnlockParams

    def run(self, inputs: Sequence[PdfInput], params: UnlockParams) -> OperationResult:
        item = inputs[0]
        ensure_pdf(item.data, item.name)
        # Caminho primário: pypdf decifra e regrava sem criptografia.
        reader = pe.open_reader(item.data, params.password)
        try:
            writer = pe.clone_writer(reader)
            data = pe.write_bytes(writer)
        except Exception:
            # Fallback robusto para documentos que o pypdf não regrava bem.
            data = pike.remove_password(item.data, params.password)
        artifact = Artifact(data=data, filename=safe_filename(params.output_name))
        return OperationResult(artifacts=[artifact], meta={"encrypted": False})
