import typing
from collections.abc import Callable
from dataclasses import dataclass, is_dataclass
from typing import Any, Generic, TypeVar

from .runner import CliRunner

T = TypeVar("T")

__all__ = ["EntryPoint"]


@dataclass
class EntryPoint(Generic[T]):
    method: Callable[..., T]
    argument_class: type[Any] | None = None

    def __call__(self) -> T:
        self.setup_argument_class()
        if self.argument_class is None:
            result = CliRunner.run_with_cli_args(self.method)
        else:
            instance = CliRunner.run_with_cli_args(self.argument_class)
            result = self.method(instance)
        typed_result = typing.cast(T, result)
        return typed_result

    def setup_argument_class(self) -> None:
        if self.argument_class is None:
            self.extract_argument_class()
        if self.argument_class is not None:
            self.argument_class.__doc__ = self.method.__doc__

    def extract_argument_class(self) -> None:
        type_hints = typing.get_type_hints(self.method)
        type_hints.pop("return", None)
        type_hint_values = type_hints.values()
        if type_hint_values:
            type_hint = next(iter(type_hint_values))
            if is_dataclass(type_hint):
                self.argument_class = type_hint
