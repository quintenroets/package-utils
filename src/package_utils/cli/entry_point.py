import sys
from collections.abc import Callable
from functools import partial
from inspect import Parameter
from typing import Any, TypeVar

from .convertor import Convertor
from .declarations import resolvable_without_parser

T = TypeVar("T")


def create_entry_point(
    method: Callable[..., object], argument_class: type[Any] | None = None
) -> Callable[[], None]:
    return partial(run_entry_point, method, argument_class)


def run_entry_point(
    method: Callable[..., object], argument_class: type[Any] | None
) -> None:
    if argument_class is None:
        invoke_from_cli_args(method)
    else:
        method(invoke_from_cli_args(argument_class, method.__doc__))


def invoke_from_cli_args(
    object_: Callable[..., T] | type[T], documentation: str | None = None
) -> T:
    convertor = Convertor(object_, documentation_override=documentation)
    return convertor.create_value(load_arguments(convertor))


def load_arguments(convertor: Convertor[Any]) -> dict[str, Any]:
    parameters = convertor.parameters
    if parser_should_be_skipped(parameters):
        arguments = {parameter.name: parameter.default for parameter in parameters}
    else:
        from .parser import parse_cli_args  # noqa: PLC0415

        arguments = parse_cli_args(convertor)
    return arguments


def parser_should_be_skipped(parameters: list[Parameter]) -> bool:
    return (
        not sys.argv[1:]
        and sys.modules.get("typer") is None
        and all(resolvable_without_parser(parameter) for parameter in parameters)
    )
