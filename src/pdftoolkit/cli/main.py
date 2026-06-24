"""CLI do toolkit, gerada a partir do registro de operações.

Comandos:
    ptk list                       lista as operações disponíveis
    ptk schema <operacao>          mostra o schema JSON dos parâmetros
    ptk run <operacao> [arquivos]  executa uma operação
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, get_origin

import typer

from pdftoolkit.core.errors import PdfToolkitError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.registry import all_operations, get_operation

app = typer.Typer(
    add_completion=False,
    help="Concentrador de operações de PDF.",
    no_args_is_help=True,
)


@app.command("list")
def list_operations() -> None:
    """Lista todas as operações registradas."""
    for operation in all_operations():
        typer.echo(f"{operation.name:<16} [{operation.category}] {operation.summary}")


@app.command("schema")
def show_schema(operation: str) -> None:
    """Mostra o schema JSON dos parâmetros de uma operação."""
    op = _lookup(operation)
    schema = op.params_model.model_json_schema()
    typer.echo(json.dumps(schema, indent=2, ensure_ascii=False))


@app.command("run")
def run(
    operation: str,
    inputs: Annotated[list[Path] | None, typer.Argument(help="PDFs de entrada")] = None,
    param: Annotated[
        list[str] | None,
        typer.Option("-p", "--param", help="Parâmetro k=v (repita para listas)"),
    ] = None,
    json_params: Annotated[
        str | None, typer.Option("--json", help="Parâmetros como objeto JSON")
    ] = None,
    out: Annotated[
        Path | None, typer.Option("-o", "--out", help="Diretório de saída")
    ] = None,
) -> None:
    """Executa uma operação sobre os PDFs informados."""
    op = _lookup(operation)
    raw = json.loads(json_params) if json_params else _parse_params(param or [])
    try:
        params = op.params_model(**_coerce_list_fields(op, raw))
        pdf_inputs = [PdfInput(path.read_bytes(), path.name) for path in inputs or []]
        result = op.execute(pdf_inputs, params)
    except PdfToolkitError as exc:
        typer.secho(f"erro: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not result.artifacts:
        typer.echo(json.dumps(result.meta, indent=2, ensure_ascii=False))
        return

    out_dir = out or Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    for artifact in result.artifacts:
        destination = out_dir / artifact.filename
        destination.write_bytes(artifact.data)
        typer.echo(f"escrito: {destination}")


def _lookup(name: str) -> PdfOperation[Any]:
    try:
        return get_operation(name)
    except PdfToolkitError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc


def _parse_params(pairs: list[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise typer.BadParameter(f"esperado k=v, recebido {pair!r}")
        key = key.strip()
        if key in parsed:
            existing = parsed[key]
            parsed[key] = [*existing, value] if isinstance(existing, list) else [existing, value]
        else:
            parsed[key] = value
    return parsed


def _coerce_list_fields(op: PdfOperation[Any], raw: dict[str, Any]) -> dict[str, Any]:
    """Embrulha valores escalares em lista quando o campo correspondente é uma lista."""
    fields = op.params_model.model_fields
    coerced: dict[str, Any] = {}
    for key, value in raw.items():
        field = fields.get(key)
        is_list_field = field is not None and get_origin(field.annotation) is list
        if is_list_field and not isinstance(value, list):
            value = [value]
        coerced[key] = value
    return coerced


if __name__ == "__main__":  # pragma: no cover
    app()
