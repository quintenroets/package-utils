from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

from .convertor import Convertor
from .parser import parse_cli_args

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
    return convertor.create_value(parse_cli_args(convertor))
