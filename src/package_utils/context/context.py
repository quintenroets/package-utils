from __future__ import annotations

import os
import typing
from functools import cached_property
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from .lazy_secrets import create_lazy_secrets
from .models import Config as Config_
from .models import Models
from .models import Options as Options_
from .models import Secrets as Secrets_

if TYPE_CHECKING:  # pragma: nocover
    from _typeshed import DataclassInstance
    from superpathlib import Path

T = TypeVar("T")


class Context(Generic[Options_, Config_, Secrets_]):
    def __init__(
        self,
        Options: type[Options_] | None = None,  # noqa: N803
        Config: type[Config_] | None = None,  # noqa: N803
        Secrets: type[Secrets_] | None = None,  # noqa: N803
    ) -> None:
        self.models = Models[Options_, Config_, Secrets_](Options, Config, Secrets)

    @cached_property
    def options(self) -> Options_:
        model = typing.cast("type[DataclassInstance] | None", self.models.Options)
        options = None if model is None else model()
        return typing.cast("Options_", options)

    @cached_property
    def config(self) -> Config_:
        model = typing.cast("type[DataclassInstance] | None", self.models.Config)
        if model is None:
            config = None
        else:
            optional_path = getattr(self.options, "config_path", None)
            path = typing.cast("Path | None", optional_path)
            config = model() if path is None else load_from_file(model, path)
        return typing.cast("Config_", config)

    @cached_property
    def secrets(self) -> Secrets_:
        model = typing.cast("type[DataclassInstance] | None", self.models.Secrets)
        secrets = None if model is None else create_lazy_secrets(model)
        return typing.cast("Secrets_", secrets)

    @cached_property
    def is_running_in_ci(self) -> bool:
        return (
            "GITHUB_ACTIONS" in os.environ and "PYTEST_CURRENT_TEST" not in os.environ
        )


def load_from_file(model: type[T], path: Path) -> T:
    import dacite  # noqa: PLC0415
    from superpathlib import Path  # noqa: PLC0415

    config = dacite.Config(type_hooks={Path: Path}, strict=True)
    info = typing.cast("dict[str, Any]", path.yaml)
    return dacite.from_dict(model, info, config=config)
