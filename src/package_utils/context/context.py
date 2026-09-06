import os
import typing
from functools import cached_property
from typing import TYPE_CHECKING, Generic

from .lazy_secrets import create_lazy_secrets
from .loaders import Loaders
from .models import Config as Config_
from .models import Models
from .models import Options as Options_
from .models import Secrets as Secrets_

if TYPE_CHECKING:  # pragma: nocover
    from _typeshed import DataclassInstance


class Context(Generic[Options_, Config_, Secrets_]):
    def __init__(
        self,
        Options: type[Options_] | None = None,  # noqa: N803
        Config: type[Config_] | None = None,  # noqa: N803
        Secrets: type[Secrets_] | None = None,  # noqa: N803
    ) -> None:
        self.models = Models[Options_, Config_, Secrets_](Options, Config, Secrets)
        self.loaders = Loaders(self.models)

    @property
    def options(self) -> Options_:
        return self.loaders.options.value

    @options.setter
    def options(self, options: Options_) -> None:
        self.loaders.options.value = options

    @property
    def config(self) -> Config_:
        return self.loaders.config.value

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
