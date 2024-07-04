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

    def __post_init__(self) -> None:
        self.signature = inspect.signature(self.object)
        self.annotations = typing.get_type_hints(self.annotated_method)

    def run(self) -> Method[T]:
        method = self.create_cli_entry_method()
        method.__signature__ = self.create_signature_for_cli_entry()  # type: ignore[attr-defined]
        return method

    def create_cli_entry_method(self) -> Method[T]:
        return self.object

    def create_signature_for_cli_entry(self) -> inspect.Signature:
        parameters_iterator = self.create_parameters_for_cli_entry()
        parameters = list(parameters_iterator)
        return self.signature.replace(parameters=parameters)

    def create_parameters_for_cli_entry(self) -> Iterator[inspect.Parameter]:
        parameters = self.extract_parameters_info()
        for parameter in parameters:
            yield parameter.convert()

    def extract_parameters_info(self) -> Iterator[CliParameter]:
        for parameter in self.signature.parameters.values():
            annotation = self.annotations[parameter.name]
            yield CliParameter(parameter, annotation)
