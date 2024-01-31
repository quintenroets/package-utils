from typing import Generic

from .loaders import Loaders
from .models import Config as Config_
from .models import Models
from .models import Options as Options_
from .models import Secrets as Secrets_


class Context(Generic[Options_, Config_, Secrets_]):
    def __init__(
        self,
        Options: type[Options_] | None = None,
        Config: type[Config_] | None = None,
        Secrets: type[Secrets_] | None = None,
    ) -> None:
        models = Models[Options_, Config_, Secrets_](Options, Config, Secrets)
        self.loaders = Loaders(models)

    @property
    def options(self) -> Options_:
        return self.loaders.options.value

    @options.setter
    def options(self, options: Options_) -> None:
        self.loaders.options.value = options

    @property
    def config(self) -> Config_:
        return self.loaders.config.value

    @property
    def secrets(self) -> Secrets_:
        return self.loaders.secrets.value
