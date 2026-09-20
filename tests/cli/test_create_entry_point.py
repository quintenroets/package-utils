from __future__ import annotations

from inspect import signature
from typing import TYPE_CHECKING, Annotated, cast

import pytest
from package_dev_utils.tests.args import cli_args, no_cli_args

from package_utils.cli import create_entry_point

if TYPE_CHECKING:
    from collections.abc import Callable  # pragma: nocover

from tests.cli.models import dataclass_model, deferred_typer_model
from tests.utils import run_isolated

default_options = dataclass_model.Options()


def run(options: Options) -> str:
    """
    Normal method.
    """
    return options.message


def run_with_arguments(message: str = dataclass_model.Options.message) -> str:
    """
    Method with arguments.
    """
    return message


def run_annotated(options: Annotated[Options, "metadata"]) -> str:
    """
    Method with annotated options.
    """
    return options.message


def run_undocumented(options: dataclass_model.Options) -> str:
    return options.message


def run_union(options: int | Options) -> str:
    return cast("Options", options).message


def print_message(options: Options) -> None:
    print(options.message)  # noqa: T201


class Options(dataclass_model.Options):
    def run(self: Options) -> str:
        """
        Instance method.
        """
        return self.message


def run_mixed(
    verbose: bool = False,  # noqa: FBT001, FBT002
    options: dataclass_model.Options = default_options,
) -> str:
    return f"{options.message} {verbose}"


def run_undocumented_with_two_dataclasses(
    options: dataclass_model.Options,
    nested: dataclass_model.NestedOptionsWithoutDefaults = (
        dataclass_model.default_nested_options
    ),
) -> str:
    return f"{options.message} {nested.use_nesting}"


@pytest.fixture
def methods() -> tuple[Callable[..., str], ...]:
    return (
        run,
        run_with_arguments,
        run_annotated,
        run_undocumented,
        run_union,
        Options.run,
        run_mixed,
        run_undocumented_with_two_dataclasses,
    )


@pytest.fixture
def documented_methods(
    methods: tuple[Callable[..., str], ...],
) -> tuple[Callable[..., str], ...]:
    return tuple(method for method in methods if method.__doc__)


@no_cli_args
def test_discarded_result() -> None:
    assert create_entry_point(lambda: "result")() is None


@no_cli_args
def test_specified_class() -> None:
    entry_point = create_entry_point(Options.run, Options)
    assert entry_point() is None


@cli_args("--message", "custom")
def test_supported_methods(methods: tuple[Callable[..., str], ...]) -> None:
    for method in methods:
        create_entry_point(method)()


@cli_args("--message", "custom")
def test_received_options(capsys: pytest.CaptureFixture[str]) -> None:
    create_entry_point(print_message)()
    assert capsys.readouterr().out.strip() == "custom"


@cli_args("--help")
def test_method_docstring(
    documented_methods: tuple[Callable[..., str], ...],
    capsys: pytest.CaptureFixture[str],
) -> None:
    for method in documented_methods:
        entry_point = create_entry_point(method)
        with pytest.raises(SystemExit) as exception:
            entry_point()
        assert exception.value.code == 0

        assert method.__doc__ is not None
        assert method.__doc__.strip() in capsys.readouterr().out


@pytest.mark.parametrize(
    ("method", "documented"),
    [
        (run_undocumented, True),
        (run_mixed, True),
        (run_undocumented_with_two_dataclasses, False),
    ],
)
@cli_args("--help")
def test_class_docstring(
    method: Callable[..., str],
    documented: bool,  # noqa: FBT001
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exception:
        create_entry_point(method)()
    assert exception.value.code == 0
    assert dataclass_model.Options.__doc__ is not None
    is_documented = dataclass_model.Options.__doc__.strip() in capsys.readouterr().out
    assert is_documented == documented


@no_cli_args
def test_signature_preserved() -> None:
    original = signature(run_with_arguments)
    create_entry_point(run_with_arguments)()
    assert signature(run_with_arguments) == original


@no_cli_args
def test_skipping_the_parser_yields_the_declared_defaults() -> None:
    options = create_entry_point(dataclass_model.FlatOptions)()
    assert options == dataclass_model.FlatOptions()


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
    """The whole saving is the import, so only its absence proves the optimization."""
    source = """
import sys
from tests.cli.models.deferred_typer_model import DeferredOptions
from package_utils.cli import create_entry_point
create_entry_point(DeferredOptions)()
assert "typer" not in sys.modules, "the fast path imported typer"
"""
    run_isolated(source)
