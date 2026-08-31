import sys
from collections.abc import Callable
from dataclasses import is_dataclass
from functools import partial
from typing import Any, TypeVar, cast

import typer

from package_utils.annotations import first_parameter_types

from . import convertors

T = TypeVar("T")


def create_entry_point(
    method: Callable[..., T], argument_class: type[Any] | None = None
) -> Callable[[], T]:
    return partial(run_entry_point, method, argument_class)


def instantiate_from_cli_args(class_: type[T], documented_object: object = None) -> T:
    if documented_object is not None:
        class_.__doc__ = documented_object.__doc__
    return run_with_cli_args(class_)


def run_entry_point(method: Callable[..., T], argument_class: type[Any] | None) -> T:
    if argument_class is None:
        argument_class = extract_argument_class(method)
    if argument_class is not None and method.__doc__ is not None:
        argument_class.__doc__ = method.__doc__
    return (
        run_with_cli_args(method)
        if argument_class is None
        else method(run_with_cli_args(argument_class))
    )


def extract_argument_class(method: Callable[..., Any]) -> type[Any] | None:
    types = first_parameter_types(method)
    return next((type_ for type_ in types if is_dataclass(type_)), None)


def run_with_cli_args(object_: Callable[..., T] | type[T]) -> T:
    is_dataclass_ = is_dataclass(object_)
    module = convertors.dataclass if is_dataclass_ else convertors.method
    cli_entry_method = module.Convertor(object_).run()
    app = typer.Typer(add_completion=False)
    app.command()(cli_entry_method)
    result_or_exit_code = app(standalone_mode=False)
    if isinstance(result_or_exit_code, int):
        sys.exit(result_or_exit_code)
    return cast("T", result_or_exit_code)
