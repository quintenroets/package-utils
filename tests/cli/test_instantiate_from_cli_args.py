from __future__ import annotations

from dataclasses import dataclass, field

import click
import pytest
from _pytest.monkeypatch import MonkeyPatch
from package_dev_utils.tests.args import cli_args, no_cli_args
from package_utils.cli import instantiate_from_cli_args
from plib import Path
from pytest import CaptureFixture


@dataclass
class Options:
    """
    Options.
    """

    debug: bool = False
    config_path: Path = Path.draft
    log_path: Path | None = None
    verbosity: int = field(init=False)
    message: str = "Hello World!"

    def __post_init__(self) -> None:
        self.verbosity = 0


@no_cli_args
def test_defaults() -> None:
    options = instantiate_from_cli_args(Options)
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


@cli_args("--verbosity", 1)
def test_verbosity_attribute_not_exposed(monkeypatch: MonkeyPatch) -> None:
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
