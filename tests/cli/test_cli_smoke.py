"""Smoke do adaptador de CLI."""

from __future__ import annotations

from typer.testing import CliRunner

from pdftoolkit.cli.main import app
from pdftoolkit.engines import pypdf_engine as pe

runner = CliRunner()


def test_list_shows_operations():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "merge" in result.stdout


def test_schema_outputs_json():
    result = runner.invoke(app, ["schema", "split"])
    assert result.exit_code == 0
    assert '"every"' in result.stdout


def test_run_merge_writes_files(tmp_path, make_pdf):
    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    a.write_bytes(make_pdf(2, "A"))
    b.write_bytes(make_pdf(3, "B"))
    out = tmp_path / "saida"
    result = runner.invoke(app, ["run", "merge", str(a), str(b), "-o", str(out)])
    assert result.exit_code == 0, result.stdout
    produced = list(out.glob("*.pdf"))
    assert len(produced) == 1
    assert pe.count_pages(produced[0].read_bytes()) == 5


def test_run_split_with_param(tmp_path, make_pdf):
    src = tmp_path / "x.pdf"
    src.write_bytes(make_pdf(5))
    out = tmp_path / "out"
    result = runner.invoke(app, ["run", "split", str(src), "-p", "every=2", "-o", str(out)])
    assert result.exit_code == 0, result.stdout
    assert len(list(out.glob("*.pdf"))) == 3


def test_run_metadata_read_prints_json(tmp_path, make_pdf):
    src = tmp_path / "x.pdf"
    src.write_bytes(make_pdf(3))
    result = runner.invoke(app, ["run", "metadata-read", str(src)])
    assert result.exit_code == 0
    assert "/Pages" in result.stdout


def test_unknown_operation_fails(tmp_path):
    result = runner.invoke(app, ["run", "inexistente"])
    assert result.exit_code != 0
