import functools
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from inspect import Parameter, Signature, signature
from typing import Any, Generic, TypeVar

from .parameter import convert, typer_namespace

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
        @functools.wraps(self.object, assigned=("__doc__",), updated=())
        def entry_method(**kwargs: Any) -> T:
            return self.call(**kwargs)

        return entry_method

    def call(self, **kwargs: Any) -> T:
        return self.object(**kwargs)

    def extract_parameters(self) -> Iterator[Parameter]:
        signature_ = signature(self.object, eval_str=True, locals=typer_namespace)
        yield from signature_.parameters.values()
