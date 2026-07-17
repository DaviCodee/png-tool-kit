"""CLI do toolkit, gerada a partir do registro de operações.

Cada operação registrada vira um subcomando próprio, com flags derivadas do seu modelo
de parâmetros Pydantic:

    pik list                          lista as operações disponíveis
    pik schema <operacao>             mostra o schema JSON dos parâmetros
    pik resize foto.png --width 800 -o saida/
    pik convert foto.png --format webp -o out/
    pik favicon logo.png -o out/

Um caminho de diretório é expandido recursivamente (arquivos ocultos ignorados), filtrado
pela whitelist de extensões de imagem — sobreponível com ``--ext``.
"""

from __future__ import annotations

import json
import types
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Union, get_args, get_origin

import click

from pngtoolkit.core.errors import ImageToolkitError
from pngtoolkit.core.io import ImageInput
from pngtoolkit.core.operation import ImageOperation
from pngtoolkit.core.registry import all_operations, get_operation

_RESERVED = {"list", "schema", "batch-convert"}
_PY_TYPES: dict[type, type] = {int: int, float: float, str: str}

# Extensões consideradas ao expandir diretórios (arquivos passados explicitamente
# nunca são filtrados). ``--ext`` sobrepõe esta lista.
_FOLDER_WHITELIST: frozenset[str] = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".avif",
})


@click.group(help="Concentrador de operações de imagem.")
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


def _help_for(field: Any, fallback: str) -> str:
    """Usa a descrição do campo Pydantic como ajuda da flag; senão o fallback."""
    return field.description or fallback


def _build_option(name: str, field: Any) -> click.Option:
    flag = "--" + name.replace("_", "-")
    annotation, optional = _unwrap_optional(field.annotation)
    origin = get_origin(annotation)
    required = field.is_required()
    default = None if field.is_required() else field.default

    if annotation is bool:
        return click.Option(
            [f"{flag}/--no-{name.replace('_', '-')}", name],
            default=default, help=_help_for(field, ""),
        )
    if origin is Literal:
        choices = [str(value) for value in get_args(annotation)]
        return click.Option(
            [flag, name], type=click.Choice(choices), default=default,
            required=required, help=_help_for(field, ""),
        )
    if origin is list:
        element, _ = _unwrap_optional(get_args(annotation)[0])
        return click.Option(
            [flag, name], type=_PY_TYPES.get(element, str), multiple=True,
            help=_help_for(field, "repita a flag para múltiplos valores"),
        )
    if origin is tuple:
        element, _ = _unwrap_optional(get_args(annotation)[0])
        nargs = len(get_args(annotation))
        fallback = f"informe {nargs} valores separados por espaço"
        return click.Option(
            [flag, name], type=_PY_TYPES.get(element, str), nargs=nargs,
            help=_help_for(field, fallback),
        )
    if origin is dict:
        return click.Option(
            [flag, name], multiple=True, metavar="CHAVE=VALOR",
            help=_help_for(field, "repita a flag; formato chave=valor"),
        )
    return click.Option(
        [flag, name], type=_PY_TYPES.get(annotation, str), default=default,
        required=required, help=_help_for(field, ""),
    )


def _collect_params(
    op: ImageOperation[Any], ctx: click.Context, raw: dict[str, Any]
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
        elif get_origin(annotation) is list:
            payload[name] = list(value)
        else:
            payload[name] = value
    return payload


def _split_pair(item: str) -> tuple[str, str]:
    key, sep, value = item.partition("=")
    if not sep:
        raise click.BadParameter(f"esperado chave=valor, recebido {item!r}")
    return key.strip(), value


def _resolve_whitelist(exts: tuple[str, ...]) -> frozenset[str] | None:
    if not exts:
        return _FOLDER_WHITELIST
    return frozenset(
        ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in exts
    )


def _expand_paths(
    paths: tuple[str, ...], extensions: frozenset[str] | None
) -> list[tuple[Path, str]]:
    """Expande diretórios recursivamente em pares (caminho, nome_relativo)."""
    resolved: list[tuple[Path, str]] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.is_dir():
            resolved.append((path, path.name))
            continue
        found = [
            (p, p.relative_to(path).as_posix())
            for p in sorted(path.rglob("*"))
            if p.is_file()
            and not any(part.startswith(".") for part in p.relative_to(path).parts)
            and (extensions is None or p.suffix.lower() in extensions)
        ]
        if not found:
            raise click.ClickException(f"nenhum arquivo compatível em: {path}")
        resolved.extend(found)
    return resolved


def _make_operation_command(op: ImageOperation[Any]) -> click.Command:
    def callback(**raw: Any) -> None:
        ctx = click.get_current_context()
        paths = raw.pop("inputs")
        out = raw.pop("out")
        exts = raw.pop("ext")
        try:
            payload = _collect_params(op, ctx, raw)
            params = op.params_model(**payload)
            pairs = _expand_paths(paths, _resolve_whitelist(exts))
            image_inputs = [ImageInput(p.read_bytes(), rel) for p, rel in pairs]
            result = op.execute(image_inputs, params)
        except (ImageToolkitError, OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        _emit(result, out)

    params: list[click.Parameter] = [
        click.Argument(["inputs"], nargs=-1, required=op.min_inputs > 0),
        click.Option(
            ["-o", "--out", "out"], type=click.Path(path_type=Path), help="diretório de saída"
        ),
        click.Option(
            ["--ext", "ext"], multiple=True,
            help="extensões aceitas ao expandir pastas (padrão: whitelist do toolkit)",
        ),
        click.Option(["--json", "json_params"], help="parâmetros como objeto JSON"),
    ]
    params.extend(
        _build_option(name, field)
        for name, field in op.params_model.model_fields.items()
    )
    return click.Command(name=op.name, params=params, callback=callback, help=op.summary)


def _safe_destination(out: Path, filename: str) -> Path:
    """Resolve o destino de um artefato, rejeitando path absoluto ou traversal."""
    relative = PurePosixPath(filename)
    if relative.is_absolute() or ".." in relative.parts:
        raise click.ClickException(f"nome de artefato inválido: {filename}")
    return out / relative


def _emit(result: Any, out: Path | None) -> None:
    if result.artifacts:
        out_dir = out or Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)
        for artifact in result.artifacts:
            destination = _safe_destination(out_dir, artifact.filename)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(artifact.data)
            click.echo(f"escrito: {destination}")
    if result.meta:
        click.echo(json.dumps(result.meta, indent=2, ensure_ascii=False))


def _lookup(name: str) -> ImageOperation[Any]:
    try:
        return get_operation(name)
    except ImageToolkitError as exc:
        raise click.ClickException(str(exc)) from exc


def _register_operation_commands() -> None:
    for operation in all_operations():
        if operation.name in _RESERVED:
            continue
        app.add_command(_make_operation_command(operation))


@app.command("batch-convert")
@click.argument("inputs", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--out", "out_dir",
    type=click.Path(path_type=Path),
    help="diretório de saída (padrão: mesma pasta de cada origem).",
)
@click.option(
    "--delete-originals/--keep-originals",
    default=False,
    help="apaga cada arquivo de origem após a conversão bem-sucedida.",
)
@click.option(
    "--format", "format_",
    type=click.Choice(["png", "jpg", "webp", "gif", "bmp", "avif"]),
    default="webp",
    help="formato de saída.",
)
@click.option(
    "--quality", type=click.IntRange(1, 100), default=None,
    help="qualidade (1–100) para formatos com perda (jpg/webp/avif).",
)
def batch_convert_command(
    inputs: tuple[Path, ...],
    out_dir: Path | None,
    delete_originals: bool,
    format_: str,
    quality: int | None,
) -> None:
    """Converte todas as imagens dentro de PASTA(s), recursivamente."""
    if not inputs:
        raise click.ClickException("informe ao menos uma pasta de origem")
    op = get_operation("batch-convert")
    params = op.params_model.model_validate(
        {"format": format_, "quality": quality, "delete_originals": delete_originals}
    )

    converted = 0
    for folder in inputs:
        if not folder.is_dir():
            raise click.ClickException(f"não é uma pasta: {folder}")
        target_dir = (out_dir or folder).resolve()
        try:
            sources = _expand_paths((str(folder),), _FOLDER_WHITELIST)
        except click.ClickException:
            click.echo(f"nenhuma imagem em {folder}")
            continue

        try:
            image_inputs = [
                ImageInput(path.read_bytes(), rel) for path, rel in sources
            ]
            result = op.execute(image_inputs, params)
        except (ImageToolkitError, OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

        if len(result.artifacts) != len(sources):
            raise click.ClickException(
                f"operação devolveu {len(result.artifacts)} artefatos para "
                f"{len(sources)} entradas; abortando antes de apagar originais"
            )

        for art, (_src, _) in zip(result.artifacts, sources, strict=True):
            destination = target_dir / art.filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(art.data)
            click.echo(f"escrito: {destination}")
        converted += len(result.artifacts)

        if delete_originals:
            for src, _ in sources:
                src.unlink()
                click.echo(f"removido: {src}")

    click.echo(f"convertidos: {converted}")


_register_operation_commands()


if __name__ == "__main__":  # pragma: no cover
    app()
