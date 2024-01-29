from typing import Generic

from .loaders import Loaders
from .models import Config, Models, Options, Secrets


class Context(Generic[Options, Config, Secrets]):
    def __init__(self, models: Models[Options, Config, Secrets] | None = None):
        if models is None:
            models = Models()
        self.loaders = Loaders(models)

    @property
    def options(self) -> Options | None:
        return self.loaders.options.value

    @options.setter
    def options(self, options: Options | None) -> None:
        self.loaders.options.value = options

    @property
    def config(self) -> Config | None:
        return self.loaders.config.value

    @property
    def secrets(self) -> Secrets | None:
        return self.loaders.secrets.value
