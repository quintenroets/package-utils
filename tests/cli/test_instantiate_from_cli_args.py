from __future__ import annotations

from dataclasses import dataclass, field

import click
import pytest
from _pytest.monkeypatch import MonkeyPatch
from package_dev_tools.utils.tests import clear_cli_args, set_cli_args
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


def test_defaults(monkeypatch: MonkeyPatch) -> None:
    clear_cli_args(monkeypatch)
    options = instantiate_from_cli_args(Options)
    assert options.debug == Options.debug
    assert options.config_path == Options.config_path
    assert options.log_path == Options.log_path


def test_debug_attribute_true(monkeypatch: MonkeyPatch) -> None:
    set_cli_args(monkeypatch, "--debug")
    options = instantiate_from_cli_args(Options)
    assert options.debug is True


def test_debug_attribute_false(monkeypatch: MonkeyPatch) -> None:
    set_cli_args(monkeypatch, "--no-debug")
    options = instantiate_from_cli_args(Options)
    assert options.debug is False


def test_config_path(monkeypatch: MonkeyPatch) -> None:
    with Path.tempfile() as tmp:
        set_cli_args(monkeypatch, "--config-path", tmp)
        options = instantiate_from_cli_args(Options)
        assert options.config_path == tmp


def test_log_path(monkeypatch: MonkeyPatch) -> None:
    with Path.tempfile() as tmp:
        set_cli_args(monkeypatch, "--log-path", tmp)
        options = instantiate_from_cli_args(Options)
        assert options.log_path == tmp


def test_message(monkeypatch: MonkeyPatch) -> None:
    message = "Hello!"
    set_cli_args(monkeypatch, "--message", message)
    options = instantiate_from_cli_args(Options)
    assert options.message == message


def test_verbosity_attribute_not_exposed(monkeypatch: MonkeyPatch) -> None:
    set_cli_args(monkeypatch, "--verbosity", 1)
    with pytest.raises(click.exceptions.NoSuchOption):
        instantiate_from_cli_args(Options)


def test_help(monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]) -> None:
    set_cli_args(monkeypatch, "--help")
    with pytest.raises(SystemExit) as exception:
        instantiate_from_cli_args(Options)
    assert exception.value.code == 0

    captured = capsys.readouterr()
    assert "Usage: " in captured.out
    assert str(Options.__doc__).strip() in captured.out
