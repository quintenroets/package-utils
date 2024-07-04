from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import typer  # noqa: TCH002

from tests.cli.models.dataclass_model import Action  # noqa: TCH001

if TYPE_CHECKING:
    from superpathlib import Path  # pragma: nocover


from tests.cli.models import dataclass_model


class Options:
    """
    Options.
    """

    def __init__(  # noqa: PLR0913
        self,
        action: Annotated[Action, typer.Argument()] = dataclass_model.Options.action,
        ignore_paths: Annotated[list[Path] | None, typer.Argument()] = None,
        action_on_error: Action = dataclass_model.Options.action_on_error,
        debug: bool = dataclass_model.Options.debug,  # noqa: FBT001
        config_path: Path = dataclass_model.Options.config_path,
        log_path: Path | None = dataclass_model.Options.log_path,
        message: str = dataclass_model.Options.message,
        messages: list[str] | None = None,
        optional_message: str | None = dataclass_model.Options.optional_message,
        n_retries: int = 0,
    ) -> None:
        self.action = action
        self.ignore_paths = [] if ignore_paths is None else ignore_paths
        self.action_on_error = action_on_error
        self.debug = debug
        self.config_path = config_path
        self.log_path = log_path
        self.verbosity = 0
        self.message = message
        self.messages = [] if messages is None else messages
        self.optional_message = optional_message
        self.n_retries = n_retries
