from __future__ import annotations

from inspect import signature
from typing import TYPE_CHECKING, Annotated, cast

import pytest
from package_dev_utils.tests.args import cli_args, no_cli_args

from package_utils.cli import create_entry_point
from package_utils.cli.entry_point import run_with_cli_args

if TYPE_CHECKING:
    from collections.abc import Callable  # pragma: nocover

from tests.cli.models import dataclass_model


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


@pytest.fixture
def methods() -> tuple[Callable[..., str], ...]:
    return (
        run,
        run_with_arguments,
        run_annotated,
        run_undocumented,
        run_union,
        Options.run,
    )


@pytest.fixture
def documented_methods(
    methods: tuple[Callable[..., str], ...],
) -> tuple[Callable[..., str], ...]:
    return tuple(method for method in methods if method.__doc__)


@no_cli_args
def test_default_result() -> None:
    assert run_with_cli_args(run_with_arguments) == Options.message


@cli_args("--message", "custom")
def test_custom_result() -> None:
    assert run_with_cli_args(run_with_arguments) == "custom"


@no_cli_args
def test_integer_result() -> None:
    assert run_with_cli_args(lambda: 1) == 1


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


@cli_args("--help")
def test_class_docstring(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exception:
        create_entry_point(run_undocumented)()
    assert exception.value.code == 0
    assert dataclass_model.Options.__doc__ is not None
    assert dataclass_model.Options.__doc__.strip() in capsys.readouterr().out


@no_cli_args
def test_signature_preserved() -> None:
    original = signature(run_with_arguments)
    create_entry_point(run_with_arguments)()
    assert signature(run_with_arguments) == original
