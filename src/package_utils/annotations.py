from __future__ import annotations

import inspect
import operator
from dataclasses import is_dataclass
from functools import reduce
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

    from _typeshed import DataclassInstance  # pragma: nocover


def first_parameter_types(method: Callable[..., Any]) -> Iterator[type]:
    return base_types_of(first_parameter_annotation(method))


def first_parameter_annotation(method: Callable[..., Any]) -> object | None:
    name = next(iter(inspect.signature(method).parameters), None)
    return name and get_type_hints(method, include_extras=True).get(name)


def dataclass_of(annotation: object) -> type[DataclassInstance] | None:
    types = (type_ for type_ in base_types_of(annotation) if is_dataclass(type_))
    return next(types, None)


def base_types_of(annotation: object) -> Iterator[type]:
    origin = origin_of(annotation)
    if origin is UnionType or origin is Union:
        for argument in get_args(annotation):
            if argument is not NoneType:
                yield from base_types_of(argument)
    elif origin is Annotated:
        yield from base_types_of(get_args(annotation)[0])
    elif origin is Literal:
        for argument in get_args(annotation):
            yield type(argument)
    elif isinstance(origin, type):
        yield origin
    elif hasattr(origin, "__value__"):
        yield from base_types_of(expand_alias(origin, get_args(annotation)))


def resolve_aliases(annotation: object) -> Any:
    origin = origin_of(annotation)
    arguments = get_args(annotation)
    if hasattr(origin, "__value__"):
        resolution = resolve_aliases(expand_alias(origin, arguments))
    else:
        resolved_arguments = tuple(resolve_aliases(argument) for argument in arguments)
        if resolved_arguments == arguments:
            resolution = annotation
        elif origin is UnionType:
            resolution = reduce(operator.or_, resolved_arguments)
        else:
            resolution = origin[resolved_arguments]
    return resolution


def origin_of(annotation: object) -> Any:
    return get_origin(annotation) or annotation


def expand_alias(alias: Any, arguments: tuple[Any, ...]) -> Any:
    return alias.__value__[arguments] if arguments else alias.__value__
