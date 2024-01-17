import typing
from collections.abc import Callable
from dataclasses import dataclass, is_dataclass
from typing import Any, Generic, TypeVar

from .cli_runner import Runner

T = TypeVar("T")


@dataclass
class EntryPoint(Generic[T]):
    method: Callable[..., T]
    argument_class: type[Any] | None = None

    def __call__(self) -> T:
        self.setup_argument_class()
        if self.argument_class is None:
            result = Runner(self.method).run_with_cli_args()
        else:
            instance = Runner(self.argument_class).run_with_cli_args()
            result = self.method(instance)
        return result

    def setup_argument_class(self) -> None:
        if self.argument_class is None:
            self.extract_argument_class()
        if self.argument_class is not None:
            method_doc = self.method.__doc__
            if method_doc is not None:
                self.argument_class.__doc__ = method_doc

    def extract_argument_class(self) -> None:
        type_hints = typing.get_type_hints(self.method)
        type_hints.pop("return", None)
        type_hint_values = type_hints.values()
        if type_hint_values:
            type_hint = next(iter(type_hint_values))
            if is_dataclass(type_hint):
                self.argument_class = type_hint
