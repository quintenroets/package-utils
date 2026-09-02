import functools
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from inspect import Parameter, Signature, signature
from typing import Any, Generic, TypeVar

from package_utils.cli.return_value import ReturnValue

from .parameter import convert, typer_namespace

T = TypeVar("T")


@dataclass
class Convertor(Generic[T]):
    object: Callable[..., T]

    def create_command(self) -> Callable[..., ReturnValue[T]]:
        @functools.wraps(self.object, assigned=("__doc__",), updated=())
        def command(**kwargs: Any) -> ReturnValue[T]:
            return ReturnValue(self.call(**kwargs))

        parameters = [convert(parameter) for parameter in self.extract_parameters()]
        command.__signature__ = Signature(parameters=parameters)  # type: ignore[attr-defined]
        return command

    def call(self, **kwargs: Any) -> T:
        return self.object(**kwargs)

    def extract_parameters(self) -> Iterator[Parameter]:
        signature_ = signature(self.object, eval_str=True, locals=typer_namespace)
        yield from signature_.parameters.values()
