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
