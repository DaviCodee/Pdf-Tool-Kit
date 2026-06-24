"""Assinatura digital via pyHanko (extra ``sign``).

Aceita um certificado PKCS#12 (.pfx) do usuário ou gera um par autoassinado efêmero
para testes. Importação preguiçosa.
"""

from __future__ import annotations

import datetime
from io import BytesIO
from typing import Any

from pdftoolkit.core.errors import InvalidInputError, MissingDependencyError, OperationError
from pdftoolkit.core.workspace import temp_workspace

_EPHEMERAL_PASSPHRASE = b"pdftoolkit-ephemeral"


def _signers() -> Any:
    try:
        from pyhanko.sign import signers
    except ImportError as exc:
        raise MissingDependencyError(
            "assinatura requer o extra 'sign' (pip install pdftoolkit[sign])"
        ) from exc
    return signers


def _make_ephemeral_pkcs12() -> bytes:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "pdftoolkit ephemeral")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"pdftoolkit",
        key,
        cert,
        None,
        serialization.BestAvailableEncryption(_EPHEMERAL_PASSPHRASE),
    )


def sign(
    data: bytes,
    *,
    pkcs12_data: bytes | None = None,
    passphrase: str | None = None,
    field_name: str = "Signature1",
    reason: str | None = None,
    location: str | None = None,
    ephemeral: bool = False,
) -> bytes:
    """Assina o PDF e devolve a nova versão assinada."""
    signers = _signers()
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

    if pkcs12_data is not None:
        pfx_bytes = pkcs12_data
        secret = passphrase.encode() if passphrase else None
    elif ephemeral:
        pfx_bytes = _make_ephemeral_pkcs12()
        secret = _EPHEMERAL_PASSPHRASE
    else:
        raise InvalidInputError(
            "forneça um certificado .pfx ou use ephemeral=true para um certificado de teste"
        )

    with temp_workspace() as workspace:
        pfx_path = workspace / "cert.pfx"
        pfx_path.write_bytes(pfx_bytes)
        try:
            signer = signers.SimpleSigner.load_pkcs12(str(pfx_path), passphrase=secret)
        except Exception as exc:
            raise InvalidInputError(f"certificado inválido ou senha incorreta: {exc}") from exc
        if signer is None:
            raise InvalidInputError("não foi possível carregar o certificado")

        meta = signers.PdfSignatureMetadata(
            field_name=field_name, reason=reason, location=location
        )
        writer = IncrementalPdfFileWriter(BytesIO(data))
        try:
            output = signers.sign_pdf(writer, meta, signer=signer)
        except Exception as exc:
            raise OperationError(f"falha ao assinar: {exc}") from exc
        return bytes(output.getvalue())
