import sys
from collections.abc import Callable
from dataclasses import is_dataclass
from functools import partial
from typing import TYPE_CHECKING, Any, TypeVar

import typer

from package_utils.annotations import first_parameter_types

from . import convertors

if TYPE_CHECKING:
    from .return_value import ReturnValue

T = TypeVar("T")


def create_entry_point(
    method: Callable[..., object], argument_class: type[Any] | None = None
) -> Callable[[], None]:
    return partial(run_entry_point, method, argument_class)


def instantiate_from_cli_args(class_: type[T], documented_object: object = None) -> T:
    if documented_object is not None:
        class_.__doc__ = documented_object.__doc__
    return run_with_cli_args(class_)


def run_entry_point(
    method: Callable[..., object], argument_class: type[Any] | None
) -> None:
    if argument_class is None:
        argument_class = extract_argument_class(method)
    if argument_class is not None and method.__doc__ is not None:
        argument_class.__doc__ = method.__doc__
    if argument_class is None:
        run_with_cli_args(method)
    else:
        method(run_with_cli_args(argument_class))


def extract_argument_class(method: Callable[..., Any]) -> type[Any] | None:
    types = first_parameter_types(method)
    return next((type_ for type_ in types if is_dataclass(type_)), None)


def run_with_cli_args(object_: Callable[..., T] | type[T]) -> T:
    module = convertors.dataclass if is_dataclass(object_) else convertors.method
    command = module.Convertor(object_).create_command()
    app = typer.Typer(add_completion=False)
    app.command()(command)
    result: ReturnValue[T] | int = app(standalone_mode=False)
    if isinstance(result, int):
        sys.exit(result)
    return result.value
