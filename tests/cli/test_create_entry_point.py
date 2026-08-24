from __future__ import annotations

from inspect import signature
from typing import TYPE_CHECKING, Annotated

import pytest
from package_dev_utils.tests.args import cli_args, no_cli_args

from package_utils.cli import create_entry_point

if TYPE_CHECKING:
    from collections.abc import Callable  # pragma: nocover

from tests.cli.models import dataclass_model


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


def run_annotated(options: Annotated[Options, "metadata"]) -> str | None:
    """
    Method with annotated options.
    """
    return run(options)


def run_undocumented(options: dataclass_model.Options) -> str | None:
    return run_with_arguments(debug=options.debug, message=options.message)


class Options(dataclass_model.Options):
    def run(self: Options) -> str | None:
        """
        Instance method.
        """
        return run(self)


@pytest.fixture
def methods(
    documented_methods: tuple[Callable[..., str | None], ...],
) -> tuple[Callable[..., str | None], ...]:
    return (*documented_methods, run_undocumented)


@pytest.fixture
def documented_methods() -> tuple[Callable[..., str | None], ...]:
    return run_with_arguments, run, run_annotated, Options.run


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
    documented_methods: tuple[Callable[..., str | None], ...],
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
