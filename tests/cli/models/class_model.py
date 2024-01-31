from typing import Annotated

import typer
from plib import Path

from tests.cli.models import dataclass_model
from tests.cli.models.dataclass_model import Action


class Options:
    """
    Options.
    """

    def __init__(
        self,
        action: Annotated[Action, typer.Argument()] = dataclass_model.Options.action,
        action_on_error: Action = dataclass_model.Options.action_on_error,
        debug: bool = dataclass_model.Options.debug,
        config_path: Path = dataclass_model.Options.config_path,
        log_path: Path | None = dataclass_model.Options.log_path,
        message: str = dataclass_model.Options.message,
        optional_message: str | None = dataclass_model.Options.optional_message,
        n_retries: int = 0,
    ) -> None:
        self.action = action
        self.action_on_error = action_on_error
        self.debug = debug
        self.config_path = config_path
        self.log_path = log_path
        self.verbosity = 0
        self.message = message
        self.optional_message = optional_message
        self.n_retries = n_retries
