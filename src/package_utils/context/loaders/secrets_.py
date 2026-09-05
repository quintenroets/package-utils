from __future__ import annotations

import dataclasses
import os
import shlex
import subprocess
import typing
from dataclasses import dataclass, fields, is_dataclass
from typing import Generic, TypeVar, cast, get_type_hints

import dacite

from package_utils.context.models import Secrets

from . import options

if typing.TYPE_CHECKING:  # pragma: nocover
    from _typeshed import DataclassInstance


T = TypeVar("T", bound="DataclassInstance")


@dataclass
class SecretLoader:
    name: str

    def load(self) -> str:
        env_name = self.name.upper().replace(" ", "_")
        value = os.environ.get(env_name)
        if not value and (askpass := os.environ.get("SECRET_ASKPASS")):
            command = [*shlex.split(askpass), self.name]
            value = subprocess.check_output(command).decode().strip()  # noqa: S603
        if not value:
            message = (
                f"Secret {self.name!r} not found (set {env_name} or SECRET_ASKPASS)"
            )
            raise RuntimeError(message)
        return value


@dataclass
class DataclassLoader(Generic[T]):
    class_: type[T]

    def load(self) -> T:
        return dacite.from_dict(self.class_, {})


@dataclass
class Loader(options.Loader[Secrets]):
    def load(self) -> DataclassInstance:
        self.add_defaults(self.typed_model)
        return dacite.from_dict(self.typed_model, {})

    def add_defaults(
        self,
        class_type: type[DataclassInstance],
        parent_name: str = "",
    ) -> None:
        type_hints = get_type_hints(class_type)
        for field in fields(class_type):
            name = field.name
            full_name = f"{parent_name}_{name}" if parent_name else name
            if field.default_factory == dataclasses.MISSING:
                type_ = type_hints[name]
                if is_dataclass(type_):
                    nested_class = cast("type[DataclassInstance]", type_)
                    self.add_defaults(nested_class, full_name)
                    field.default_factory = DataclassLoader(nested_class).load
                else:
                    field.default_factory = SecretLoader(full_name).load
