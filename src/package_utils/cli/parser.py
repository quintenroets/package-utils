import copy
import sys
from collections.abc import Callable
from inspect import Parameter, Signature
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.models import ParameterInfo

from package_utils.annotations import contained_class_of, resolve_aliases

from .convertor import Convertor


def parse_cli_args(convertor: Convertor[Any]) -> dict[str, Any]:
    app = typer.Typer(add_completion=False)
    app.command()(create_command(convertor))
    result: dict[str, Any] | int = app(standalone_mode=False)
    if isinstance(result, int):
        sys.exit(result)
    return result


def create_command(convertor: Convertor[Any]) -> Callable[..., dict[str, Any]]:
    def command(**arguments: Any) -> dict[str, Any]:
        return arguments

    command.__doc__ = convertor.documentation
    parameters = [annotate_parameter(parameter) for parameter in convertor.parameters]
    command.__signature__ = Signature(parameters=parameters)  # type: ignore[attr-defined]
    return command


def annotate_parameter(parameter: Parameter) -> Parameter:
    annotation = resolve_aliases(parameter.annotation)
    metadata = getattr(annotation, "__metadata__", ())
    declared_type = annotation.__origin__ if metadata else annotation
    type_ = declared_type | None if parameter.default is None else declared_type
    infos = (info for info in metadata if isinstance(info, ParameterInfo))
    info = copy.copy(next(infos, typer.Option()))
    info.path_type = contained_class_of(type_, Path)
    return parameter.replace(
        annotation=Annotated[type_, info], kind=Parameter.KEYWORD_ONLY
    )
