from __future__ import annotations

import dataclasses
import os
import typing
from dataclasses import dataclass, fields, is_dataclass
from typing import Generic, cast

import cli
import dacite
from superpathlib import Path

from package_utils.context.models import Config, Options, Secrets

from . import options

if typing.TYPE_CHECKING:  # pragma: nocover
    from _typeshed import DataclassInstance

    from .config import Loader as ConfigLoader


from typing import TypeVar

T = TypeVar("T", bound="DataclassInstance")


@dataclass
class SecretLoader:
    name: str

    def load(self) -> str:
        env_name = self.name.upper()
        return os.environ.get(env_name) or cli.capture_output("pw", self.name)


@dataclass
class DataclassLoader(Generic[T]):
    class_: type[T]

    def load(self) -> T:
        return dacite.from_dict(self.class_, {})


@dataclass
class Loader(options.Loader[Secrets], Generic[Options, Config, Secrets]):
    config_loader: ConfigLoader[Options, Config] | None = None
    delimiter: str = "_"

    def load(self) -> DataclassInstance:
        self.add_defaults(self.typed_model)
        file_secrets = self.load_file_secrets()
        return dacite.from_dict(self.typed_model, file_secrets)

    def load_file_secrets(self) -> dict[str, str]:
        config = None if self.config_loader is None else self.config_loader.value
        path = config and getattr(config, "secrets_path", None)
        path = typing.cast(Path, path)
        result = {} if path is None else path.yaml
        return typing.cast(dict[str, str], result)

    def add_defaults(
        self,
        class_type: DataclassInstance | type[DataclassInstance],
        parent_name: str = "",
    ) -> None:
        for field in fields(class_type):
            name = field.name
            full_name = f"{parent_name}{self.delimiter}{name}" if parent_name else name
            if field.default_factory == dataclasses.MISSING:
                if is_dataclass(field.type):
                    self.add_defaults(field.type, full_name)
                    type_ = cast(type["DataclassInstance"], field.type)
                    field.default_factory = DataclassLoader(type_).load
                else:
                    field.default_factory = SecretLoader(full_name).load
