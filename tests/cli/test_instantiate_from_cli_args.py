from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated

import click
import pytest
import typer
from package_dev_utils.tests.args import cli_args, no_cli_args
from package_utils.cli import instantiate_from_cli_args
from plib import Path
from pytest import CaptureFixture


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

    def __post_init__(self) -> None:
        self.verbosity = 0


@no_cli_args
def test_defaults() -> None:
    options = instantiate_from_cli_args(Options)
    assert options.action == Action.show
    assert options.action_on_error == Action.show
    assert options.debug == Options.debug
    assert options.config_path == Options.config_path
    assert options.log_path == Options.log_path


@cli_args("--debug")
def test_debug_attribute_true() -> None:
    options = instantiate_from_cli_args(Options)
    assert options.debug is True


@cli_args("--no-debug")
def test_debug_attribute_false() -> None:
    options = instantiate_from_cli_args(Options)
    assert options.debug is False


def test_config_path() -> None:
    with Path.tempfile() as tmp:
        with cli_args("--config-path", tmp):
            options = instantiate_from_cli_args(Options)
            assert options.config_path == tmp


def test_log_path() -> None:
    with Path.tempfile() as tmp:
        with cli_args("--log-path", tmp):
            options = instantiate_from_cli_args(Options)
            assert options.log_path == tmp


def test_message() -> None:
    message = "Hello!"
    with cli_args("--message", message):
        options = instantiate_from_cli_args(Options)
        assert options.message == message


def test_optional_message() -> None:
    message = "Hello!"
    with cli_args("--optional-message", message):
        options = instantiate_from_cli_args(Options)
        assert options.optional_message == message


@cli_args("--verbosity", 1)
def test_verbosity_attribute_not_exposed() -> None:
    with pytest.raises(click.exceptions.NoSuchOption):
        instantiate_from_cli_args(Options)


@cli_args("--help")
def test_help(capsys: CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exception:
        instantiate_from_cli_args(Options)
    assert exception.value.code == 0

    captured = capsys.readouterr()
    assert "Usage: " in captured.out
    assert str(Options.__doc__).strip() in captured.out


@cli_args("do_nothing")
def test_positional_argument() -> None:
    options = instantiate_from_cli_args(Options)
    assert options.action == Action.do_nothing


@cli_args("--action", "do_nothing")
def test_positional_argument_no_option() -> None:
    with pytest.raises(click.exceptions.NoSuchOption):
        instantiate_from_cli_args(Options)


@cli_args("--action-on-error", "do_nothing")
def test_enum() -> None:
    options = instantiate_from_cli_args(Options)
    assert options.action_on_error == Action.do_nothing
