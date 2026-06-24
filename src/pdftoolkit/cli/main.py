"""CLI do toolkit, gerada a partir do registro de operações.

Cada operação registrada vira um subcomando próprio, com flags derivadas do seu modelo
de parâmetros Pydantic:

    ptk list                          lista as operações disponíveis
    ptk schema <operacao>             mostra o schema JSON dos parâmetros
    ptk merge a.pdf b.pdf -o saida/   executa a operação 'merge'
    ptk compress doc.pdf --quality screen -o out/
"""

from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any, Literal, Union, get_args, get_origin

import click

from pdftoolkit.core.errors import PdfToolkitError
from pdftoolkit.core.io import PdfInput
from pdftoolkit.core.operation import PdfOperation
from pdftoolkit.core.registry import all_operations, get_operation

_RESERVED = {"list", "schema"}
_PY_TYPES: dict[type, type] = {int: int, float: float, str: str}


@click.group(help="Concentrador de operações de PDF.")
def app() -> None:
    pass


@app.command("list")
def list_command() -> None:
    """Lista todas as operações registradas."""
    for operation in all_operations():
        click.echo(f"{operation.name:<16} [{operation.category}] {operation.summary}")


@app.command("schema")
@click.argument("operation")
def schema_command(operation: str) -> None:
    """Mostra o schema JSON dos parâmetros de uma operação."""
    op = _lookup(operation)
    click.echo(json.dumps(op.params_model.model_json_schema(), indent=2, ensure_ascii=False))


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        return args[0], True
    return annotation, False


def _build_option(name: str, field: Any) -> click.Option:
    flag = "--" + name.replace("_", "-")
    annotation, optional = _unwrap_optional(field.annotation)
    origin = get_origin(annotation)
    required = field.is_required()
    default = None if field.is_required() else field.default

    if annotation is bool:
        return click.Option([f"{flag}/--no-{name.replace('_', '-')}", name], default=default)
    if origin is Literal:
        choices = [str(value) for value in get_args(annotation)]
        return click.Option(
            [flag, name], type=click.Choice(choices), default=default, required=required
        )
    if origin is list:
        element, _ = _unwrap_optional(get_args(annotation)[0])
        return click.Option(
            [flag, name], type=_PY_TYPES.get(element, str), multiple=True,
            help="repita a flag para múltiplos valores",
        )
    if origin is dict:
        return click.Option(
            [flag, name], multiple=True, metavar="CHAVE=VALOR",
            help="repita a flag; formato chave=valor",
        )
    return click.Option(
        [flag, name], type=_PY_TYPES.get(annotation, str), default=default, required=required
    )


def _collect_params(
    op: PdfOperation[Any], ctx: click.Context, raw: dict[str, Any]
) -> dict[str, Any]:
    fields = op.params_model.model_fields
    payload: dict[str, Any] = {}
    json_blob = raw.get("json_params")
    if json_blob:
        payload.update(json.loads(json_blob))
    for name in fields:
        if ctx.get_parameter_source(name) == click.core.ParameterSource.DEFAULT:
            continue
        value = raw[name]
        annotation, _ = _unwrap_optional(fields[name].annotation)
        if get_origin(annotation) is dict:
            payload[name] = dict(_split_pair(item) for item in value)
        elif isinstance(value, tuple):
            payload[name] = list(value)
        else:
            payload[name] = value
    return payload


def _split_pair(item: str) -> tuple[str, str]:
    key, sep, value = item.partition("=")
    if not sep:
        raise click.BadParameter(f"esperado chave=valor, recebido {item!r}")
    return key.strip(), value


def _make_operation_command(op: PdfOperation[Any]) -> click.Command:
    def callback(**raw: Any) -> None:
        ctx = click.get_current_context()
        inputs = raw.pop("inputs")
        out = raw.pop("out")
        try:
            payload = _collect_params(op, ctx, raw)
            params = op.params_model(**payload)
            pdf_inputs = [PdfInput(Path(p).expanduser().read_bytes(), Path(p).name) for p in inputs]
            result = op.execute(pdf_inputs, params)
        except (PdfToolkitError, OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        _emit(result, out)

    params: list[click.Parameter] = [
        click.Argument(["inputs"], nargs=-1, required=op.min_inputs > 0),
        click.Option(
            ["-o", "--out", "out"], type=click.Path(path_type=Path), help="diretório de saída"
        ),
        click.Option(["--json", "json_params"], help="parâmetros como objeto JSON"),
    ]
    params.extend(
        _build_option(name, field)
        for name, field in op.params_model.model_fields.items()
    )
    return click.Command(name=op.name, params=params, callback=callback, help=op.summary)


def _emit(result: Any, out: Path | None) -> None:
    if result.artifacts:
        out_dir = out or Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)
        for artifact in result.artifacts:
            destination = out_dir / artifact.filename
            destination.write_bytes(artifact.data)
            click.echo(f"escrito: {destination}")
    if result.meta:
        click.echo(json.dumps(result.meta, indent=2, ensure_ascii=False))


def _lookup(name: str) -> PdfOperation[Any]:
    try:
        return get_operation(name)
    except PdfToolkitError as exc:
        raise click.ClickException(str(exc)) from exc


def _register_operation_commands() -> None:
    for operation in all_operations():
        if operation.name in _RESERVED:
            continue
        app.add_command(_make_operation_command(operation))


_register_operation_commands()


if __name__ == "__main__":  # pragma: no cover
    app()
