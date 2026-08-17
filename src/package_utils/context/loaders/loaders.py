from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Generic

from package_utils.context.models import Config, Models, Options, Secrets

if TYPE_CHECKING:  # pragma: nocover
    from . import config as config_module
    from . import options as options_module
    from . import secrets_ as secrets_module


class Loaders(Generic[Options, Config, Secrets]):
    def __init__(self, models: Models[Options, Config, Secrets]) -> None:
        self.models = models

    @cached_property
    def options(self) -> options_module.Loader[Options]:
        from . import options

        return options.Loader(self.models.Options)

    @cached_property
    def config(self) -> config_module.Loader[Options, Config]:
        from . import config

        return config.Loader(self.models.Config, options_loader=self.options)

    @cached_property
    def secrets(self) -> secrets_module.Loader[Options, Config, Secrets]:
        from . import secrets_

        return secrets_.Loader(self.models.Secrets, config_loader=self.config)
