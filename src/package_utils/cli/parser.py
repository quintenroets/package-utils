import copy
import sys
from collections.abc import Callable
from inspect import Parameter, Signature
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.models import ParameterInfo

from package_utils.annotations import contained_class_of, metadata_of, resolve_aliases

from .convertor import Convertor
from .declarations import DeferredInfo


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
    metadata = metadata_of(annotation)
    declared_type = annotation.__origin__ if metadata else annotation
    type_ = declared_type | None if parameter.default is None else declared_type
    info = create_info(metadata)
    info.path_type = contained_class_of(type_, Path)  # type: ignore[arg-type]
    return parameter.replace(
        annotation=Annotated[type_, info], kind=Parameter.KEYWORD_ONLY
    )


def create_info(metadata: tuple[Any, ...]) -> ParameterInfo:
    infos = (
        getattr(typer, declaration.name)(*declaration.args, **declaration.kwargs)
        if isinstance(declaration, DeferredInfo)
        else declaration
        for declaration in metadata
        if isinstance(declaration, DeferredInfo | ParameterInfo)
    )
    return copy.copy(next(infos, typer.Option()))
