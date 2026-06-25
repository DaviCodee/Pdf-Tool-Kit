"""Compressão de PDF via Ghostscript (binário de sistema ``gs``, AGPL)."""

from __future__ import annotations

from pdftoolkit.core.process import require_binary, run_command
from pdftoolkit.core.workspace import temp_workspace

# Perfis de qualidade aceitos pelo Ghostscript (-dPDFSETTINGS).
QUALITY_PROFILES = {
    "screen": "/screen",
    "ebook": "/ebook",
    "printer": "/printer",
    "prepress": "/prepress",
}


def compress(data: bytes, quality: str = "ebook") -> bytes:
    """Recomprime um PDF reduzindo a resolução de imagens conforme o perfil."""
    profile = QUALITY_PROFILES[quality]
    binary = require_binary("gs")
    with temp_workspace() as workspace:
        source = workspace / "entrada.pdf"
        target = workspace / "saida.pdf"
        source.write_bytes(data)
        run_command(
            [
                binary,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.5",
                f"-dPDFSETTINGS={profile}",
                "-dNOPAUSE",
                "-dBATCH",
                "-dQUIET",
                f"-sOutputFile={target}",
                str(source),
            ],
            cwd=workspace,
        )
        return target.read_bytes()


def to_pdfa(data: bytes, level: int = 2) -> bytes:
    """Converte um PDF para o formato PDF/A (arquivo de longa duração)."""
    if level not in (1, 2, 3):
        raise ValueError("level deve ser 1, 2 ou 3")
    binary = require_binary("gs")
    with temp_workspace() as workspace:
        source = workspace / "entrada.pdf"
        target = workspace / "saida.pdf"
        source.write_bytes(data)
        run_command(
            [
                binary,
                "-dBATCH", "-dNOPAUSE", "-dNOOUTERSAVE",
                "-sDEVICE=pdfwrite",
                f"-dPDFA={level}",
                "-dPDFACompatibilityPolicy=1",
                "-dQUIET",
                f"-sOutputFile={target}",
                str(source),
            ],
            cwd=workspace,
        )
        return target.read_bytes()


def repair(data: bytes) -> bytes:
    """Tenta reparar um PDF corrompido regravando-o via Ghostscript."""
    binary = require_binary("gs")
    with temp_workspace() as workspace:
        source = workspace / "entrada.pdf"
        target = workspace / "saida.pdf"
        source.write_bytes(data)
        run_command(
            [
                binary,
                "-dBATCH", "-dNOPAUSE",
                "-sDEVICE=pdfwrite",
                "-dQUIET",
                f"-sOutputFile={target}",
                str(source),
            ],
            cwd=workspace,
        )
        return target.read_bytes()
