from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from package_utils.context.models import Config, Options

from .options import Loader as OptionsLoader

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover
    from superpathlib import Path

T = TypeVar("T")


@dataclass
class Loader(OptionsLoader[Config], Generic[Options, Config]):
    options_loader: OptionsLoader[Options] | None = None

    def load(self) -> DataclassInstance:
        options = None if self.options_loader is None else self.options_loader.value
        optional_path = options and getattr(options, "config_path", None)
        path = typing.cast("Path | None", optional_path)
        return (
            self.typed_model()
            if path is None or not path.exists()
            else self.load_from_file(self.typed_model, path)
        )

    @classmethod
    def load_from_file(cls, class_type: type[T], path: Path) -> T:
        import dacite
        from superpathlib import Path

        config = dacite.Config(type_hooks={Path: Path}, strict=True)
        # the sidecar cache: a config read is a startup cost, and decoding it
        # costs an order of magnitude less than the PyYAML import it avoids
        info = typing.cast("dict[str, Any]", path.cached_yaml)
        return dacite.from_dict(class_type, info, config=config)
