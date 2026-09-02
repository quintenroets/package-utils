from hypothesis import given, strategies
from package_dev_utils.tests.args import cli_args, no_cli_args
from superpathlib import Path

from package_utils.context import Context
from package_utils.context.entry_point import create_entry_point
from tests.context.models.models import Config, Options, Secrets


@no_cli_args
def test_discarded_result() -> None:
    context = Context(Options, Config, Secrets)
    entry_point = create_entry_point(lambda: 1, context, lambda _: None)
    assert entry_point() is None


@given(debug=strategies.booleans())
def test_specified_options(*, debug: bool) -> None:
    def verify_options() -> None:
        assert context.options.config_path == config_path
        assert context.options.debug == debug

    context = Context(Options, Config, Secrets)
    config_path = Path.tempfile(create=False)
    debug_str = "--debug" if debug else "--no-debug"
    entry_point = create_entry_point(verify_options, context)
    with cli_args("--config-path", config_path, debug_str):
        entry_point()
