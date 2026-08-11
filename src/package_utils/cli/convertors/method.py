import inspect
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Generic, TypeVar

from .parameter import CliParameter, resolve_annotations

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
        import typer

        self.annotations = resolve_annotations(self.annotated_method, typer)
        # the same hints with the typer markers still attached: the caller's own
        # `help` lives there, and resolution is what makes it readable at all
        # when the annotations are strings
        self.declared_annotations = resolve_annotations(
            self.annotated_method,
            typer,
            include_extras=True,
        )

    def run(self) -> Method[T]:
        method = self.create_cli_entry_method()
        parameters = [
            parameter.convert() for parameter in self.extract_parameters_info()
        ]
        method.__signature__ = inspect.Signature(parameters=parameters)  # type: ignore[attr-defined]
        # typer resolves the annotations itself rather than reading the signature, so
        # leaving the originals in place would make it evaluate strings that name a
        # typer a caller deferring its own import never bound
        method.__annotations__ = {
            parameter.name: parameter.annotation for parameter in parameters
        }
        return method

    def create_cli_entry_method(self) -> Method[T]:
        return self.object

    def extract_parameters_info(self) -> Iterator[CliParameter]:
        for parameter in self.method_parameters:
            annotation = self.annotations[parameter.name]
            declared = self.declared_annotations[parameter.name]
            yield CliParameter(parameter, annotation, declared)
