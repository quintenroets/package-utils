import collections
import copy
import typing
from collections.abc import Iterator
from inspect import Parameter
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.models import ParameterInfo

typer_namespace = {"typer": typer}


def convert(parameter: Parameter) -> Parameter:
    type_ = resolve_type(parameter)
    metadata = extract_metadata(parameter)
    infos = (info for info in metadata if isinstance(info, ParameterInfo))
    info = copy.copy(next(infos, typer.Option()))
    path_classes = (
        sub_type for sub_type in extract_types(type_) if is_path_class(sub_type)
    )
    info.path_type = typing.cast("type[str] | None", next(path_classes, None))
    return parameter.replace(
        annotation=Annotated[type_, info], kind=Parameter.KEYWORD_ONLY
    )


def resolve_type(parameter: Parameter) -> Any:
    annotation = parameter.annotation
    type_ = annotation.__origin__ if extract_metadata(parameter) else annotation
    return type_ | None if parameter.default is None else type_


def extract_metadata(parameter: Parameter) -> tuple[Any, ...]:
    return getattr(parameter.annotation, "__metadata__", ())


def extract_types(root: Any) -> Iterator[object]:
    types = collections.deque([root])
    while types:
        type_ = types.popleft()
        sub_types = typing.get_args(type_)
        if sub_types:
            types.extend(sub_types)
        else:
            yield type_


def is_path_class(type_: object) -> bool:
    return isinstance(type_, type) and issubclass(type_, Path)
