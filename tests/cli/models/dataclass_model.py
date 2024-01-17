from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated

import typer
from plib import Path


class Action(Enum):
    show = "show"
    do_nothing = "do_nothing"


@dataclass
class Options:
    """
    Options.
    """

    action: Annotated[Action, typer.Argument()] = Action.show
    action_on_error: Action = Action.show
    debug: bool = False
    config_path: Path = Path.draft
    log_path: Path | None = None
    verbosity: int = field(init=False)
    message: str = "Hello World!"
    optional_message: str | None = "Hello World!"
    working_directory: Path = field(default_factory=Path.cwd)

    def __post_init__(self) -> None:
        self.verbosity = 0