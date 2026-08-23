from collections.abc import Callable, Iterator
from dataclasses import dataclass
from inspect import Parameter, Signature, signature
from typing import Generic, TypeVar

from .parameter import convert

T = TypeVar("T")
Method = Callable[..., T]


@dataclass
class Convertor(Generic[T]):
    object: Method[T]

    def run(self) -> Method[T]:
        method = self.create_cli_entry_method()
        parameters = [convert(parameter) for parameter in self.extract_parameters()]
        method.__signature__ = Signature(parameters=parameters)  # type: ignore[attr-defined]
        return method

    def create_cli_entry_method(self) -> Method[T]:
        return self.object

    def extract_parameters(self) -> Iterator[Parameter]:
        yield from signature(self.object, eval_str=True).parameters.values()
