from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Literal

import typer
from superpathlib import Path

from .help_messages import Help


@dataclass
class InnermostOptions:
    depth: int = 3


@dataclass
class InnerOptions:
    depth: int = 2
    innermost: InnermostOptions | None = None


@dataclass
class NestedOptions:
    use_nesting: bool = False
    message: Annotated[str, typer.Option("--declared-message", "-n")] = "nested"
    force: Annotated[bool, typer.Option("--force/--no-force")] = False
    inner: InnerOptions | None = None


default_parsed_nested_options = NestedOptions(
    inner=InnerOptions(innermost=InnermostOptions()),
)


@dataclass(frozen=True)
class NestedOptionsWithoutDefaults:
    use_nesting: bool


class Action(Enum):
    show = "show"
    do_nothing = "do_nothing"


default_nested_options = NestedOptionsWithoutDefaults(
    use_nesting=False,
)


class Parameters:
    action = Annotated[Action, typer.Argument(help=Help.action)]
    ignore_paths = Annotated[list[Path], typer.Argument()]
    optional_ignore_paths = Annotated[list[Path] | None, typer.Argument()]
    message = Annotated[str, typer.Option("--message", "-m", help=Help.message)]


@dataclass
class Options:
    """
    Options.
    """

    action: Parameters.action = Action.show
    ignore_paths: Parameters.ignore_paths = field(default_factory=list)
    action_on_error: Action = Action.show
    debug: bool = False
    config_path: Path = Path.draft
    log_path: Path | None = None
    verbosity: int = field(init=False)
    message: Parameters.message = "Hello World!"
    messages: list[str] = field(default_factory=list)
    optional_message: str | None = "Hello World!"
    mode: Literal["read", "write"] = "read"
    path_pair: tuple[Path, Path] = (Path.draft, Path.draft)
    working_directory: Path = field(default_factory=Path.cwd)
    n_retries: int = 0
    nested_options: NestedOptions | None = None
    nested_options_without_defaults: NestedOptionsWithoutDefaults = (
        default_nested_options
    )
    optional_nested_options_without_defaults: NestedOptionsWithoutDefaults | None = None

    def __post_init__(self) -> None:
        self.verbosity = 0
