from typing import Generic

from package_utils.context.models import Config, Models, Options, Secrets

from . import config, options, secrets_


class Loaders(Generic[Options, Config, Secrets]):
    def __init__(self, models: Models[Options, Config, Secrets]) -> None:
        self.options = options.Loader(models.Options)
        self.config = config.Loader(models.Config, options_loader=self.options)
        self.secrets = secrets_.Loader(models.Secrets, config_loader=self.config)
