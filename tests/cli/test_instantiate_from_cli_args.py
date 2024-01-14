import click
import pytest
from models import (
    class_model,
    class_model_with_string_annotations,
    dataclass_model,
    dataclass_model_with_string_annotations,
)
from models.dataclass_model import Action, Options
from package_dev_utils.tests.args import cli_args, no_cli_args
from package_utils.cli import instantiate_from_cli_args
from plib import Path
from pytest import CaptureFixture

classes = [
    class_model.Options,
    dataclass_model.Options,
    dataclass_model_with_string_annotations.Options,
    class_model_with_string_annotations.Options,
]
class_argument = pytest.mark.parametrize("class_", classes)


@no_cli_args
@pytest.mark.parametrize(
    "class_",
    [class_model.Options, class_model_with_string_annotations.Options],
)
def test_class_defaults(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    verify_defaults(options)


@no_cli_args
@pytest.mark.parametrize(
    "class_",
    [
        dataclass_model.Options,
        dataclass_model_with_string_annotations.Options,
    ],
)
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


@class_argument
@cli_args("--debug")
def test_debug_attribute_true(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    assert options.debug is True


@class_argument
@cli_args("--no-debug")
def test_debug_attribute_false(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    assert options.debug is False


@class_argument
def test_config_path(class_: type[Options]) -> None:
    with Path.tempfile() as tmp:
        with cli_args("--config-path", tmp):
            options = instantiate_from_cli_args(class_)
            assert options.config_path == tmp


@class_argument
def test_log_path(class_: type[Options]) -> None:
    with Path.tempfile() as tmp:
        with cli_args("--log-path", tmp):
            options = instantiate_from_cli_args(class_)
            assert options.log_path == tmp


@class_argument
def test_message(class_: type[Options]) -> None:
    message = "Hello!"
    with cli_args("--message", message):
        options = instantiate_from_cli_args(class_)
        assert options.message == message


@class_argument
def test_optional_message(class_: type[Options]) -> None:
    message = "Hello!"
    with cli_args("--optional-message", message):
        options = instantiate_from_cli_args(class_)
        assert options.optional_message == message


@class_argument
@cli_args("--verbosity", 1)
def test_verbosity_attribute_not_exposed(class_: type[Options]) -> None:
    with pytest.raises(click.exceptions.NoSuchOption):
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
@cli_args("do_nothing")
def test_positional_argument(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    assert options.action == Action.do_nothing


@class_argument
@cli_args("--action", "do_nothing")
def test_positional_argument_no_option(class_: type[Options]) -> None:
    with pytest.raises(click.exceptions.NoSuchOption):
        instantiate_from_cli_args(class_)


@class_argument
@cli_args("--action-on-error", "do_nothing")
def test_enum(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    assert options.action_on_error == Action.do_nothing


@pytest.mark.parametrize("class_", [dataclass_model.Options])
@cli_args("--working-directory", Path.cwd() / "subfolder")
def test_working_directory(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    assert options.working_directory == Path.cwd() / "subfolder"
