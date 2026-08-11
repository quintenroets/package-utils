from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated

import typer
from superpathlib import Path


@dataclass
class NestedOptions:
    use_nesting: bool = False


@dataclass(frozen=True)
class NestedOptionsWithoutDefaults:
    use_nesting: bool


class Action(Enum):
    show = "show"
    do_nothing = "do_nothing"


default_nested_options = NestedOptionsWithoutDefaults(
    use_nesting=False,
)


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
    nested_options_without_defaults: NestedOptionsWithoutDefaults = (
        default_nested_options
    )
    optional_nested_options_without_defaults: NestedOptionsWithoutDefaults | None = None

    def __post_init__(self) -> None:
        self.verbosity = 0


action_help = "Anticipation"
message_help = "Reverberation"


@dataclass
class FlatOptions:
    """
    Nothing nested and nothing required: a bare invocation needs no parser.
    """

    action: Annotated[Action, typer.Argument(help=action_help)] = Action.show
    debug: bool = False
    message: Annotated[str, typer.Option(help=message_help)] = "Hello World!"
    messages: list[str] = field(default_factory=list)
    verbosity: int = field(init=False)

    def __post_init__(self) -> None:
        self.verbosity = 0


@dataclass
class OptionsWithoutDefaults:
    message: str
