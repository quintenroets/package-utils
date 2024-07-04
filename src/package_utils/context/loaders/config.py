from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import dacite
from superpathlib import Path

from package_utils.context.models import Config, Options

from .options import Loader as OptionsLoader

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover

T = TypeVar("T")


@dataclass
class Loader(OptionsLoader[Config], Generic[Options, Config]):
    options_loader: OptionsLoader[Options] | None = None

    def load(self) -> DataclassInstance:
        options = None if self.options_loader is None else self.options_loader.value
        optional_path = options and getattr(options, "config_path", None)
        path = typing.cast(Path | None, optional_path)
        return (
            self.typed_model()
            if path is None
            else self.load_from_file(self.typed_model, path)
        )

    @classmethod
    def load_from_file(cls, class_type: type[T], path: Path) -> T:
        config = dacite.Config(type_hooks={Path: Path}, strict=True)
        info = typing.cast(dict[str, Any], path.yaml)
        return dacite.from_dict(class_type, info, config=config)
