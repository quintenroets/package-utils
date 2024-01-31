from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover

Model = TypeVar("Model", bound="DataclassInstance | None")


@dataclass
class Loader(Generic[Model]):
    model: type[Model] | None
    _value: Model | None = None

    @property
    def typed_model(self) -> type[DataclassInstance]:
        return typing.cast(type["DataclassInstance"], self.model)

    @property
    def value(self) -> Model:
        if self._value is None and self.model is not None:
            value = self.load()
            self.value = typing.cast(Model, value)
        return typing.cast(Model, self._value)

    @value.setter
    def value(self, value: Model | None) -> None:
        self._value = value

    def load(self) -> DataclassInstance:
        return self.typed_model()
