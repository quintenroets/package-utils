import random
from collections.abc import Iterator

import click
import pytest
from hypothesis import given, strategies
from hypothesis.strategies import SearchStrategy
from package_dev_utils.tests.args import cli_args, no_cli_args
from package_utils.cli import instantiate_from_cli_args
from pytest import CaptureFixture
from superpathlib import Path

from tests.cli.models import (
    class_model,
    class_model_with_string_annotations,
    dataclass_model,
    dataclass_model_with_string_annotations,
)
from tests.cli.models.dataclass_model import Action, Options


def text_strategy() -> SearchStrategy[str]:
    alphabet = strategies.characters(blacklist_categories=["Cc", "Cs", "Zs", "P", "S"])
    return strategies.text(alphabet=alphabet)


normal_classes = [class_model.Options, class_model_with_string_annotations.Options]
dataclasses = [dataclass_model.Options, dataclass_model_with_string_annotations.Options]
dataclass_argument = pytest.mark.parametrize("class_", dataclasses)
normal_class_argument = pytest.mark.parametrize("class_", dataclasses)
class_argument = pytest.mark.parametrize("class_", [*dataclasses, *normal_classes])


@no_cli_args
@normal_class_argument
def test_class_defaults(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    verify_defaults(options)


@no_cli_args
@dataclass_argument
def test_dataclass_defaults(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    verify_defaults(options)
    assert options.working_directory == Path.cwd()


def verify_defaults(options: Options) -> None:
    assert options.action == Action.show
    assert options.action_on_error == Action.show
    assert options.debug == Options.debug
    assert options.config_path == Options.config_path
    assert options.log_path == Options.log_path
    assert options.n_retries == Options.n_retries


@class_argument
@given(debug=strategies.booleans())
def test_debug_attribute(class_: type[Options], debug: bool) -> None:
    option_str = "--debug" if debug else "--no-debug"
    with cli_args(option_str):
        options = instantiate_from_cli_args(class_)
    assert options.debug is debug


@class_argument
def test_config_path(class_: type[Options]) -> None:
    config_path = Path.tempfile(create=False)
    with cli_args("--config-path", config_path):
        options = instantiate_from_cli_args(class_)
    assert options.config_path == config_path


@class_argument
def test_log_path(class_: type[Options]) -> None:
    log_path = Path.tempfile(create=False)
    with cli_args("--log-path", log_path):
        options = instantiate_from_cli_args(class_)
    assert options.log_path == log_path


@class_argument
@given(message=text_strategy())
def test_message(class_: type[Options], message: str) -> None:
    with cli_args("--message", message):
        options = instantiate_from_cli_args(class_)
    assert options.message == message


@class_argument
@given(message=text_strategy())
def test_optional_message(class_: type[Options], message: str) -> None:
    with cli_args("--optional-message", message):
        options = instantiate_from_cli_args(class_)
    assert options.optional_message == message


@class_argument
@given(verbosity=strategies.integers())
def test_verbosity_attribute_not_exposed(class_: type[Options], verbosity: int) -> None:
    test_args = cli_args("--verbosity", verbosity)
    expect_exception = pytest.raises(click.exceptions.NoSuchOption)
    with test_args, expect_exception:
        instantiate_from_cli_args(class_)


@class_argument
@cli_args("--help")
def test_help(class_: type[Options], capsys: CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exception:
        instantiate_from_cli_args(class_)
    assert exception.value.code == 0

    captured = capsys.readouterr()
    assert "Usage: " in captured.out
    assert str(class_.__doc__).strip() in captured.out


@class_argument
@given(action=strategies.sampled_from(Action))
def test_positional_argument(class_: type[Options], action: Action) -> None:
    with cli_args(action.value):
        options = instantiate_from_cli_args(class_)
    assert options.action == action


@class_argument
@given(action=strategies.sampled_from(Action))
def test_positional_argument_no_option(class_: type[Options], action: Action) -> None:
    test_args = cli_args("--action", action.value)
    expect_exception = pytest.raises(click.exceptions.NoSuchOption)
    with test_args, expect_exception:
        instantiate_from_cli_args(class_)


@class_argument
@given(action=strategies.sampled_from(Action))
def test_enum(class_: type[Options], action: Action) -> None:
    with cli_args("--action-on-error", action.value):
        options = instantiate_from_cli_args(class_)
    assert options.action_on_error == action


@dataclass_argument
def test_working_directory(class_: type[Options]) -> None:
    path = Path.tempfile(create=False)
    with cli_args("--working-directory", path):
        options = instantiate_from_cli_args(class_)
    assert options.working_directory == path


@class_argument
@given(n_retries=strategies.integers())
def test_type_conversion(class_: type[Options], n_retries: int) -> None:
    with cli_args("--n-retries", n_retries):
        options = instantiate_from_cli_args(class_)
    assert options.n_retries == n_retries


@class_argument
@given(
    action=strategies.sampled_from(Action),
    action_on_error=strategies.sampled_from(Action),
    debug=strategies.booleans(),
    message=text_strategy(),
    optional_message=text_strategy(),
    n_retries=strategies.integers(),
)
def test_combined_arguments(
    class_: type[Options],
    action: Action,
    action_on_error: Action,
    debug: bool,
    message: str,
    optional_message: str,
    n_retries: int,
) -> None:
    debug_string = "debug" if debug else "no-debug"
    options_dict = {
        "action-on-error": action_on_error.value,
        debug_string: None,
        "config-path": Path.tempfile(create=False),
        "log-path": Path.tempfile(create=False),
        "message": message,
        "optional-message": optional_message,
        "n-retries": n_retries,
    }
    option_arguments = generate_arguments(options_dict)
    with cli_args(action.value, *option_arguments):
        options = instantiate_from_cli_args(class_)
    assert options.action == action
    assert options.action_on_error == action_on_error
    assert options.debug == debug
    assert options.config_path == options_dict["config-path"]
    assert options.log_path == options_dict["log-path"]
    assert options.message == message
    assert options.optional_message == optional_message
    assert options.n_retries == n_retries


def generate_arguments(
    options: dict[str, int | Path | str | None], shuffle: bool = True
) -> Iterator[int | Path | str]:
    keys = list(options.keys())
    if shuffle:
        random.shuffle(keys)
    for key in keys:
        yield f"--{key}"
        value = options[key]
        if value is not None:
            yield value
