from hypothesis import given, strategies
from package_dev_utils.tests.args import cli_args, no_cli_args
from package_utils.context import Context
from package_utils.context.entry_point import create_entry_point
from superpathlib import Path

from tests.context.models.config import Config
from tests.context.models.options import Options
from tests.context.models.secrets_ import Secrets


@no_cli_args
def test_entry_point() -> None:
    context = Context(Options, Config, Secrets)
    entry_point = create_entry_point(lambda: None, context, lambda _: None)
    entry_point()


@given(debug=strategies.booleans())
def test_specified_options(debug: bool) -> None:
    def verify_options() -> None:
        assert context.options.config_path == config_path
        assert context.options.debug == debug

    context = Context(Options, Config, Secrets)
    config_path = Path.tempfile(create=False)
    debug_str = "--debug" if debug else "--no-debug"
    entry_point = create_entry_point(verify_options, context)
    with cli_args("--config-path", config_path, debug_str):
        entry_point()
