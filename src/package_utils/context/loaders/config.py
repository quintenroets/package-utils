import typing
from dataclasses import dataclass
from typing import Generic, TypeVar

import dacite
from plib import Path

from ..models import Config, Options
from .options import Loader as OptionsLoader

T = TypeVar("T")


@dataclass
class Loader(OptionsLoader[Config], Generic[Options, Config]):
    options_loader: OptionsLoader[Options] | None = None

    def load(self) -> Config:
        options = None if self.options_loader is None else self.options_loader.value
        path = options and getattr(options, "config_path", None)
        model = typing.cast(type[Config], self.model)
        return model() if path is None else self.load_from_file(model, path)

    @classmethod
    def load_from_file(cls, class_type: type[T], path: Path) -> T:
        config = dacite.Config(type_hooks={Path: Path}, strict=True)
        result = dacite.from_dict(class_type, path.yaml, config=config)
        return typing.cast(T, result)
