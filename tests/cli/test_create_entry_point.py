from __future__ import annotations

from collections.abc import Callable

import pytest
import test_instantiate_from_cli_args
from _pytest.monkeypatch import MonkeyPatch
from package_dev_utils.tests.args import cli_args, no_cli_args
from package_utils.cli import create_entry_point
from pytest import CaptureFixture


def run_with_arguments(
    debug: bool = False, message: str = test_instantiate_from_cli_args.Options.message
) -> str | None:
    """
    Method with arguments.
    """
    return message if debug else None


def run(options: Options) -> str | None:
    """
    Normal method.
    """
    return run_with_arguments(options.debug, options.message)


class Options(test_instantiate_from_cli_args.Options):
    def run(self: Options) -> str | None:
        """
        Instance method.
        """
        return run(self)


@pytest.fixture
def methods() -> tuple[Callable[..., str | None], ...]:
    return run_with_arguments, run, Options.run


@no_cli_args
def test_entry_point(methods: tuple[Callable[..., str | None], ...]) -> None:
    for method in methods:
        entry_point = create_entry_point(method)
        entry_point()


@no_cli_args
def test_with_class_specified(methods: tuple[Callable[..., str | None], ...]) -> None:
    entry_point = create_entry_point(Options.run, Options)
    entry_point()


def test_option(methods: tuple[Callable[..., str | None], ...]) -> None:
    with no_cli_args:
        for method in methods:
            entry_point = create_entry_point(method)
            result = entry_point()
            assert result is None
    with cli_args("--debug"):
        for method in methods:
            entry_point = create_entry_point(method)
            result = entry_point()
            assert result == Options.message


@cli_args("--help")
def test_docstring(
    monkeypatch: MonkeyPatch,
    methods: tuple[Callable[..., str | None], ...],
    capsys: CaptureFixture[str],
) -> None:
    for method in methods:
        entry_point = create_entry_point(method)
        with pytest.raises(SystemExit) as exception:
            entry_point()
        assert exception.value.code == 0

        captured = capsys.readouterr()
        assert str(method.__doc__).strip() in captured.out
