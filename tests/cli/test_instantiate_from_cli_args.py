import random
from collections.abc import Iterator

import pytest
from hypothesis import given, strategies
from hypothesis.strategies import SearchStrategy
from package_dev_utils.tests.args import cli_args, no_cli_args
from superpathlib import Path
from typer._click.exceptions import NoSuchOption

from package_utils.cli import instantiate_from_cli_args
from tests.cli.models import (
    class_model,
    class_model_with_string_annotations,
    dataclass_model,
    dataclass_model_with_string_annotations,
)
from tests.cli.models.dataclass_model import Action, Help, NestedOptions, Options


def text_strategy() -> SearchStrategy[str]:
    alphabet = strategies.characters(blacklist_categories=["Cc", "Cs", "Zs", "P", "S"])
    return strategies.text(alphabet=alphabet)


def path_strategy() -> SearchStrategy[Path]:
    return strategies.builds(Path, text_strategy())


normal_classes = [class_model.Options, class_model_with_string_annotations.Options]
dataclasses = [dataclass_model.Options, dataclass_model_with_string_annotations.Options]
dataclass_argument = pytest.mark.parametrize("class_", dataclasses)
normal_class_argument = pytest.mark.parametrize("class_", normal_classes)
class_argument = pytest.mark.parametrize("class_", [*dataclasses, *normal_classes])


@no_cli_args
@normal_class_argument
def test_class_defaults(class_: type[Options]) -> None:
    verify_defaults(instantiate_from_cli_args(class_))


@no_cli_args
@dataclass_argument
def test_dataclass_defaults(class_: type[Options]) -> None:
    options = instantiate_from_cli_args(class_)
    verify_defaults(options)
    assert options.working_directory == Path.cwd()


def verify_defaults(options: Options) -> None:
    assert options.action == Action.show
    assert options.ignore_paths == []
    assert options.action_on_error == Action.show
    assert options.debug == Options.debug
    assert options.config_path == Options.config_path
    assert options.log_path == Options.log_path
    assert options.messages == []
    assert options.n_retries == Options.n_retries


@class_argument
@given(debug=strategies.booleans())
def test_flag_pair(class_: type[Options], *, debug: bool) -> None:
    assert load_options(class_, flag("debug", enabled=debug)).debug is debug


@class_argument
def test_config_path(class_: type[Options]) -> None:
    config_path = Path.tempfile(create=False)
    options = load_options(class_, "--config-path", config_path)
    assert options.config_path == config_path
    assert type(options.config_path) is Path


@class_argument
def test_log_path(class_: type[Options]) -> None:
    log_path = Path.tempfile(create=False)
    options = load_options(class_, "--log-path", log_path)
    assert options.log_path == log_path
    assert type(options.log_path) is Path


@class_argument
@pytest.mark.parametrize("option_string", ["--message", "-m"])
@given(message=text_strategy())
def test_message(class_: type[Options], option_string: str, message: str) -> None:
    assert load_options(class_, option_string, message).message == message


@class_argument
@given(message=text_strategy())
def test_optional_message(class_: type[Options], message: str) -> None:
    options = load_options(class_, "--optional-message", message)
    assert options.optional_message == message


@class_argument
@given(verbosity=strategies.integers())
def test_verbosity_not_exposed(class_: type[Options], verbosity: int) -> None:
    assert_option_not_exposed(class_, "--verbosity", verbosity)


@class_argument
@cli_args("--help")
def test_help(class_: type[Options], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exception:
        instantiate_from_cli_args(class_)
    assert exception.value.code == 0
    output = capsys.readouterr().out
    expected = "Usage: ", str(class_.__doc__).strip(), Help.action, Help.message
    for text in expected:
        assert text in output


@class_argument
@given(action=strategies.sampled_from(Action))
def test_positional_argument(class_: type[Options], action: Action) -> None:
    assert load_options(class_, action.value).action == action


@class_argument
@given(action=strategies.sampled_from(Action))
def test_positional_option_not_exposed(class_: type[Options], action: Action) -> None:
    assert_option_not_exposed(class_, "--action", action.value)


@class_argument
@given(action=strategies.sampled_from(Action))
def test_enum(class_: type[Options], action: Action) -> None:
    options = load_options(class_, "--action-on-error", action.value)
    assert options.action_on_error == action


@dataclass_argument
def test_working_directory(class_: type[Options]) -> None:
    path = Path.tempfile(create=False)
    assert load_options(class_, "--working-directory", path).working_directory == path


@class_argument
@given(n_retries=strategies.integers())
def test_type_conversion(class_: type[Options], n_retries: int) -> None:
    assert load_options(class_, "--n-retries", n_retries).n_retries == n_retries


@class_argument
@given(messages=strategies.lists(text_strategy()))
def test_list_option(class_: type[Options], messages: list[str]) -> None:
    args = [value for message in messages for value in ("--messages", message)]
    assert load_options(class_, *args).messages == messages


@class_argument
@given(action=strategies.sampled_from(Action), paths=strategies.lists(path_strategy()))
def test_list_argument(
    class_: type[Options],
    action: Action,
    paths: list[Path],
) -> None:
    options = load_options(class_, action.value, *paths)
    assert options.ignore_paths == paths
    for path in options.ignore_paths:
        assert type(path) is Path


@dataclass_argument
@given(use_nesting=strategies.booleans())
def test_derived_nested_flag_pair(class_: type[Options], *, use_nesting: bool) -> None:
    option_string = flag("nested-options-use-nesting", enabled=use_nesting)
    assert load_nested_options(class_, option_string).use_nesting is use_nesting


@dataclass_argument
@pytest.mark.parametrize("option_string", ["--declared-message", "-n"])
@given(message=text_strategy())
def test_declared_nested_option(
    class_: type[Options],
    option_string: str,
    message: str,
) -> None:
    assert load_nested_options(class_, option_string, message).message == message


@dataclass_argument
@given(force=strategies.booleans())
def test_declared_nested_flag_pair(class_: type[Options], *, force: bool) -> None:
    assert load_nested_options(class_, flag("force", enabled=force)).force is force


@dataclass_argument
def test_prefixed_nested_option_not_exposed(class_: type[Options]) -> None:
    assert_option_not_exposed(class_, "--nested-options-declared-message", "message")


@class_argument
@given(
    action=strategies.sampled_from(Action),
    paths=strategies.lists(path_strategy()),
    action_on_error=strategies.sampled_from(Action),
    debug=strategies.booleans(),
    message=text_strategy(),
    messages=strategies.lists(text_strategy()),
    optional_message=text_strategy(),
    n_retries=strategies.integers(),
)
def test_combined_arguments(  # noqa: PLR0913, PLR0917
    class_: type[Options],
    action: Action,
    paths: list[Path],
    action_on_error: Action,
    debug: bool,  # noqa: FBT001
    message: str,
    messages: list[str],
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

    args = [action.value, *paths, *option_arguments]
    for message_ in messages:
        args.extend(("--messages", message_))
    options = load_options(class_, *args)
    assert options.action == action
    assert options.ignore_paths == paths
    assert options.action_on_error == action_on_error
    assert options.debug == debug
    assert options.config_path == options_dict["config-path"]
    assert options.log_path == options_dict["log-path"]
    assert options.message == message
    assert options.messages == messages
    assert options.optional_message == optional_message
    assert options.n_retries == n_retries


def load_options(class_: type[Options], *args: object) -> Options:
    with cli_args(*args):
        return instantiate_from_cli_args(class_)


def load_nested_options(class_: type[Options], *args: object) -> NestedOptions:
    nested_options = load_options(class_, *args).nested_options
    assert nested_options is not None
    return nested_options


def assert_option_not_exposed(class_: type[Options], *args: object) -> None:
    with pytest.raises(NoSuchOption):
        load_options(class_, *args)


def flag(name: str, *, enabled: bool) -> str:
    return f"--{name}" if enabled else f"--no-{name}"


def generate_arguments(
    options: dict[str, int | Path | str | None],
    *,
    shuffle: bool = True,
) -> Iterator[int | Path | str]:
    keys = list(options.keys())
    if shuffle:
        random.shuffle(keys)
    for key in keys:
        yield f"--{key}"
        value = options[key]
        if value is not None:
            yield value
