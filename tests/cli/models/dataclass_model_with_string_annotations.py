from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated

from superpathlib import Path

from .dataclass_model import (
    Action,
    NestedOptions,
    NestedOptionsWithoutDefaults,
    default_nested_options,
)
from .help_messages import Help

if TYPE_CHECKING:
    import typer  # pragma: nocover


@dataclass
class Options:
    """
    Options.
    """

    action: Annotated[Action, typer.Argument(help=Help.action)] = Action.show
    ignore_paths: Annotated[list[Path], typer.Argument()] = field(default_factory=list)
    action_on_error: Action = Action.show
    debug: bool = False
    config_path: Path = Path.draft
    log_path: Path | None = None
    verbosity: int = field(init=False)
    message: Annotated[str, typer.Option("--message", "-m", help=Help.message)] = (
        "Hello World!"
    )
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
