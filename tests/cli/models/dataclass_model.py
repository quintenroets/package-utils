from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated

import typer
from superpathlib import Path


@dataclass
class NestedOptions:
    use_nesting: bool = False


class Action(Enum):
    show = "show"
    do_nothing = "do_nothing"


@dataclass
class Options:
    """
    Options.
    """

    action: Annotated[Action, typer.Argument()] = Action.show
    ignore_paths: Annotated[list[Path], typer.Argument()] = field(default_factory=list)
    action_on_error: Action = Action.show
    debug: bool = False
    config_path: Path = Path.draft
    log_path: Path | None = None
    verbosity: int = field(init=False)
    message: str = "Hello World!"
    messages: list[str] = field(default_factory=list)
    optional_message: str | None = "Hello World!"
    working_directory: Path = field(default_factory=Path.cwd)
    n_retries: int = 0
    nested_options: NestedOptions | None = None

    def __post_init__(self) -> None:
        self.verbosity = 0
