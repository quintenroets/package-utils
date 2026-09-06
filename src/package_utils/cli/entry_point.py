import sys
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from inspect import Signature
from typing import Any, Generic, TypeVar

import typer

from .convertor import Convertor
from .parameter import create_typer_parameter

T = TypeVar("T")


@dataclass
class ReturnValue(Generic[T]):
    value: T


def create_entry_point(
    method: Callable[..., object], argument_class: type[Any] | None = None
) -> Callable[[], None]:
    return partial(run_entry_point, method, argument_class)


def instantiate_from_cli_args(class_: type[T], documented_object: object = None) -> T:
    documentation = None if documented_object is None else documented_object.__doc__
    return run_with_cli_args(class_, documentation)


def run_entry_point(
    method: Callable[..., object], argument_class: type[Any] | None
) -> None:
    if argument_class is None:
        run_with_cli_args(method)
    else:
        method(run_with_cli_args(argument_class, method.__doc__))


def run_with_cli_args(
    object_: Callable[..., T] | type[T], documentation: str | None = None
) -> T:
    app = typer.Typer(add_completion=False)
    app.command()(create_command(object_, documentation))
    result: ReturnValue[T] | int = app(standalone_mode=False)
    if isinstance(result, int):
        sys.exit(result)
    return result.value


def create_command(
    object_: Callable[..., T] | type[T], documentation: str | None
) -> Callable[..., ReturnValue[T]]:
    convertor = Convertor(object_)

    def command(**arguments: Any) -> ReturnValue[T]:
        return ReturnValue(convertor.create_value(arguments))

    parameters = [
        create_typer_parameter(parameter)
        for parameter in convertor.extract_cli_parameters()
    ]
    command.__doc__ = (
        documentation or object_.__doc__ or convertor.parameter_documentation
    )
    command.__signature__ = Signature(parameters=parameters)  # type: ignore[attr-defined]
    return command
