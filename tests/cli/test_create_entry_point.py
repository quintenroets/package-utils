from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from package_dev_utils.tests.args import cli_args, no_cli_args

from package_utils.cli import create_entry_point
from package_utils.cli.entry_point import defaults_cover_arguments

if TYPE_CHECKING:
    from collections.abc import Callable  # pragma: nocover

from tests.cli.models import dataclass_model, deferred_typer_model


def run_with_arguments(
    *,
    debug: bool = False,
    message: str = dataclass_model.Options.message,
) -> str | None:
    """
    Method with arguments.
    """
    return message if debug else None


def run(options: Options) -> str | None:
    """
    Normal method.
    """
    return run_with_arguments(debug=options.debug, message=options.message)


class Options(dataclass_model.Options):
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
def test_with_class_specified() -> None:
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
    methods: tuple[Callable[..., str | None], ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    for method in methods:
        entry_point = create_entry_point(method)
        with pytest.raises(SystemExit) as exception:
            entry_point()
        assert exception.value.code == 0

        captured = capsys.readouterr()
        assert str(method.__doc__).strip() in captured.out


@no_cli_args
def test_flat_defaults_skip_the_parser() -> None:
    """Building a parser imports typer, which costs more than the whole run."""
    assert defaults_cover_arguments(dataclass_model.FlatOptions)


@no_cli_args
def test_skipping_the_parser_yields_the_declared_defaults() -> None:
    options = create_entry_point(dataclass_model.FlatOptions)()
    assert options == dataclass_model.FlatOptions()


@cli_args("--debug")
def test_arguments_need_the_parser() -> None:
    assert not defaults_cover_arguments(dataclass_model.FlatOptions)


@no_cli_args
def test_nested_dataclass_needs_the_parser() -> None:
    """Nested fields are flattened and rebuilt, so the outer default never applies."""
    assert not defaults_cover_arguments(dataclass_model.Options)


@no_cli_args
def test_missing_default_needs_the_parser() -> None:
    assert not defaults_cover_arguments(dataclass_model.OptionsWithoutDefaults)


@no_cli_args
def test_plain_method_needs_the_parser() -> None:
    assert not defaults_cover_arguments(run_with_arguments)


@cli_args("--help")
def test_declared_help_reaches_the_parser(capsys: pytest.CaptureFixture[str]) -> None:
    """Rebuilding the marker used to drop the `help=` the caller declared."""
    entry_point = create_entry_point(dataclass_model.FlatOptions)
    with pytest.raises(SystemExit):
        entry_point()
    captured = capsys.readouterr()
    assert dataclass_model.action_help in captured.out
    assert dataclass_model.message_help in captured.out


@no_cli_args
def test_deferred_typer_yields_the_declared_defaults() -> None:
    options = create_entry_point(deferred_typer_model.DeferredOptions)()
    assert options == deferred_typer_model.DeferredOptions()


@cli_args("--debug")
def test_deferred_typer_reaches_the_parser() -> None:
    """Resolving the parser's hints used to need the import the model withheld."""
    options = create_entry_point(deferred_typer_model.DeferredOptions)()
    assert options == deferred_typer_model.DeferredOptions(debug=True)


@cli_args("--help")
def test_deferred_typer_keeps_the_declared_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    entry_point = create_entry_point(deferred_typer_model.DeferredOptions)
    with pytest.raises(SystemExit):
        entry_point()
    captured = capsys.readouterr()
    assert deferred_typer_model.action_help in captured.out
    assert deferred_typer_model.message_help in captured.out


def test_bare_invocation_never_imports_typer() -> None:
    """
    The whole saving is the import, so only its absence proves the optimization.

    A subprocess is the only place it can be observed: any other test in this
    process has already put typer in `sys.modules`.
    """
    source = """
import sys
from tests.cli.models.deferred_typer_model import DeferredOptions
from package_utils.cli import create_entry_point
create_entry_point(DeferredOptions)()
assert "typer" not in sys.modules, "the fast path imported typer"
"""
    root = Path(__file__).parent.parent.parent
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join((str(root / "src"), str(root))),
    }
    subprocess.run(  # noqa: S603
        [sys.executable, "-c", source],
        check=True,
        env=environment,
        cwd=root,
    )
