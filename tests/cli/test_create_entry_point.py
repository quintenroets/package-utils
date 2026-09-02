from __future__ import annotations

from inspect import signature
from typing import TYPE_CHECKING, Annotated, cast

import pytest
from package_dev_utils.tests.args import cli_args, no_cli_args

from package_utils.cli import create_entry_point

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
def test_with_class_specified() -> None:
    entry_point = create_entry_point(Options.run, Options)
    entry_point()


def test_option(methods: tuple[Callable[..., str], ...]) -> None:
    with no_cli_args:
        for method in methods:
            assert create_entry_point(method)() == Options.message
    with cli_args("--message", "custom"):
        for method in methods:
            assert create_entry_point(method)() == "custom"


@cli_args("--help")
def test_docstring(
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
def test_class_docstring_preserved(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exception:
        create_entry_point(run_undocumented)()
    assert exception.value.code == 0
    assert dataclass_model.Options.__doc__ is not None
    assert dataclass_model.Options.__doc__.strip() in capsys.readouterr().out


@no_cli_args
def test_original_signature_preserved() -> None:
    original = signature(run_with_arguments)
    create_entry_point(run_with_arguments)()
    assert signature(run_with_arguments) == original
