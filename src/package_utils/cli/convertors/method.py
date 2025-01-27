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
        return self.object

    @property
    def method_parameters(self) -> Iterator[inspect.Parameter]:
        yield from inspect.signature(self.object).parameters.values()

    def __post_init__(self) -> None:
        self.annotations = typing.get_type_hints(self.annotated_method)

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
        for parameter in self.method_parameters:
            annotation = self.annotations[parameter.name]
            yield CliParameter(parameter, annotation)
