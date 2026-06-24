"""Contrato base de uma operação de PDF.

Toda operação é uma classe que declara metadados (nome, categoria, resumo), o modelo
de parâmetros e quantos documentos de entrada aceita, além de implementar ``run``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar, Generic, TypeVar

from pdftoolkit.core.errors import InvalidInputError
from pdftoolkit.core.io import OperationResult, PdfInput
from pdftoolkit.core.params import OperationParams

P = TypeVar("P", bound=OperationParams)


class PdfOperation(ABC, Generic[P]):
    """Unidade de trabalho do toolkit.

    Subclasses fixam o tipo de parâmetro via ``PdfOperation[MeuParams]`` e definem os
    atributos de classe abaixo.
    """

    name: ClassVar[str]
    category: ClassVar[str]
    summary: ClassVar[str]
    params_model: ClassVar[type[OperationParams]]
    min_inputs: ClassVar[int] = 1
    max_inputs: ClassVar[int | None] = 1

    def check_inputs(self, inputs: Sequence[PdfInput]) -> None:
        """Valida a quantidade de documentos de entrada."""
        count = len(inputs)
        if count < self.min_inputs:
            raise InvalidInputError(
                f"operação {self.name!r} exige ao menos {self.min_inputs} arquivo(s), "
                f"recebeu {count}"
            )
        if self.max_inputs is not None and count > self.max_inputs:
            raise InvalidInputError(
                f"operação {self.name!r} aceita no máximo {self.max_inputs} arquivo(s), "
                f"recebeu {count}"
            )

    @abstractmethod
    def run(self, inputs: Sequence[PdfInput], params: P) -> OperationResult:
        """Executa a operação e devolve o resultado."""

    def execute(self, inputs: Sequence[PdfInput], params: P) -> OperationResult:
        """Valida as entradas e chama :meth:`run`."""
        self.check_inputs(inputs)
        return self.run(inputs, params)
