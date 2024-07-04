from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import TypeVar

from . import method
from .parameter import CliParameter

T = TypeVar("T")


@dataclass
class Convertor(method.Convertor[T]):
    object: type[T]

    @property
    def annotated_method(self) -> Callable[..., T]:
        return self.object.__init__  # type: ignore[return-value]

    def extract_parameters_info(self) -> Iterator[CliParameter]:
        for parameter in self.signature.parameters.values():
            if parameter.name != "self":
                annotation = self.annotations[parameter.name]
                yield CliParameter(parameter, annotation)
