import collections
import copy
import typing
from collections.abc import Iterator
from inspect import Parameter
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.models import ParameterInfo

from package_utils.annotations import resolve_aliases

typer_namespace = {"typer": typer}


def create_typer_parameter(parameter: Parameter) -> Parameter:
    annotation = resolve_aliases(parameter.annotation)
    metadata = getattr(annotation, "__metadata__", ())
    declared_type = annotation.__origin__ if metadata else annotation
    type_ = declared_type | None if parameter.default is None else declared_type
    infos = (info for info in metadata if isinstance(info, ParameterInfo))
    info = copy.copy(next(infos, typer.Option()))
    path_classes = (
        sub_type for sub_type in extract_types(type_) if is_path_class(sub_type)
    )
    info.path_type = typing.cast("type[str] | None", next(path_classes, None))
    return parameter.replace(
        annotation=Annotated[type_, info], kind=Parameter.KEYWORD_ONLY
    )


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
