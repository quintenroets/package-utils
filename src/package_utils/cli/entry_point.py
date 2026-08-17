import inspect
from collections.abc import Callable
from dataclasses import dataclass, is_dataclass
from typing import Any, Generic, TypeVar

from package_utils.annotations import first_parameter_types

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
        if self.argument_class is None and inspect.isfunction(self.method):
            self.extract_argument_class()
        if self.argument_class is not None:
            method_doc = self.method.__doc__
            if method_doc is not None:
                self.argument_class.__doc__ = method_doc

    def extract_argument_class(self) -> None:
        argument_class = next(first_parameter_types(self.method), None)
        if is_dataclass(argument_class):
            self.argument_class = argument_class
