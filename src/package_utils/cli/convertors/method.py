import inspect
import typing
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

from .parameter import CliParameter

T = TypeVar("T")
Method = Callable[..., T]


@dataclass
class Convertor(Generic[T]):
    object: Method[T]

    @property
    def annotated_method(self) -> Method[T]:
        is_class = inspect.isclass(self.object)
        return self.object.__init__ if is_class else self.object  # type: ignore[return-value]

    def __post_init__(self) -> None:
        method = self.annotated_method
        self.annotations = typing.get_type_hints(method, include_extras=True)

    def run(self) -> Method[T]:
        method = self.create_cli_entry_method()
        parameters = [
            parameter.convert() for parameter in self.extract_parameters_info()
        ]
        method.__signature__ = inspect.Signature(parameters=parameters)  # type: ignore[attr-defined]
        return method

    def create_cli_entry_method(self) -> Method[T]:
        return self.object

    def extract_parameters_info(self) -> Iterator[CliParameter]:
        for parameter in inspect.signature(self.object).parameters.values():
            annotation = self.annotations[parameter.name]
            yield CliParameter(parameter, annotation)
