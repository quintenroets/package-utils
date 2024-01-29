import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover

Model = TypeVar("Model", bound="DataclassInstance")


@dataclass
class Loader(Generic[Model]):
    model: type[Model] | None = None
    _value: Model | None = None

    @property
    def value(self) -> Model | None:
        if self._value is None and self.model is not None:
            self._value = self.load()
        return self._value

    @value.setter
    def value(self, value: Model | None) -> None:
        self._value = value

    def load(self) -> Model:
        self.model = typing.cast(type[Model], self.model)
        return self.model()
