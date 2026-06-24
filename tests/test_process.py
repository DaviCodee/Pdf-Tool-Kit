"""Testes do executor de processos externos."""

from __future__ import annotations

import pytest

from pdftoolkit.core.errors import MissingDependencyError, OperationError
from pdftoolkit.core.process import require_binary, run_command


def test_require_binary_missing():
    with pytest.raises(MissingDependencyError):
        require_binary("binario-que-nao-existe-12345")


def test_require_binary_found():
    assert require_binary("python3").endswith("python3")


def test_run_command_success():
    result = run_command(["python3", "-c", "print('ok')"])
    assert result.stdout.decode().strip() == "ok"


def test_run_command_failure_raises():
    with pytest.raises(OperationError):
        run_command(["python3", "-c", "import sys; sys.exit(2)"])
