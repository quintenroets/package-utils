from __future__ import annotations

import inspect
from types import NoneType, UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


def first_parameter_types(method: Callable[..., Any]) -> Iterator[type]:
    annotation = first_parameter_annotation(method)
    if annotation is not None:
        yield from base_types_of(annotation)


def first_parameter_annotation(method: Callable[..., Any]) -> object | None:
    name = next(iter(inspect.signature(method).parameters), None)
    return name and get_type_hints(method, include_extras=True).get(name)


def base_types_of(annotation: object) -> Iterator[type]:
    origin = get_origin(annotation)
    resolved_annotation = annotation if origin is None else origin
    if resolved_annotation is UnionType or resolved_annotation is Union:
        for argument in get_args(annotation):
            if argument is not NoneType:
                yield from base_types_of(argument)
    elif resolved_annotation is Annotated:
        yield from base_types_of(get_args(annotation)[0])
    elif resolved_annotation is Literal:
        for argument in get_args(annotation):
            yield type(argument)
    elif isinstance(resolved_annotation, type):
        yield resolved_annotation
    else:
        type_alias: Any = resolved_annotation
        yield from base_types_of(type_alias.__value__)
