"""Hierarquia de erros do toolkit.

Os adaptadores traduzem essas exceções em códigos de saída (CLI) ou status HTTP (API).
"""

from __future__ import annotations


class PdfToolkitError(Exception):
    """Raiz de todos os erros tratáveis do toolkit."""


class InvalidInputError(PdfToolkitError):
    """Entrada inválida: arquivo não é PDF, parâmetro fora de faixa, etc."""


class PageRangeError(InvalidInputError):
    """Especificação de intervalo de páginas malformada ou fora dos limites."""


class EncryptedPdfError(PdfToolkitError):
    """PDF protegido por senha que não pôde ser aberto com a senha fornecida."""


class OperationError(PdfToolkitError):
    """Falha durante a execução de uma operação (motor retornou erro)."""


class MissingDependencyError(PdfToolkitError):
    """Funcionalidade requer uma dependência/binário opcional não instalado."""
