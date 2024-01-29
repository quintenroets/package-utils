from unittest.mock import patch

from package_utils.context import Context as Context_
from package_utils.context import Models

from tests.context.models.config import Config
from tests.context.models.options import Options
from tests.context.models.secrets_ import Secrets

Context = Context_[Config, Options, Secrets]


def test_empty_context() -> None:
    context = Context()
    assert context.options is None
    assert context.config is None
    assert context.secrets is None


def test_options() -> None:
    models = Models(Options=Options)
    context = Context(models)
    assert isinstance(context.options, Options)
    assert context.options.debug == Options.debug
    assert context.options.config_path == Options.config_path
    assert context.config is None
    assert context.secrets is None


def test_config() -> None:
    models = Models(Config=Config)
    context = Context(models)
    assert isinstance(context.config, Config)
    assert context.config.output_path == Config.output_path
    assert context.config.secrets_path == Config.secrets_path
    assert context.options is None
    assert context.secrets is None


def test_secrets() -> None:
    models = Models(Secrets=Secrets)
    context = Context(models)
    with patch("cli.get"):
        assert isinstance(context.secrets, Secrets)
    assert context.options is None
    assert context.config is None


def test_full_context() -> None:
    models = Models(Options=Options, Config=Config, Secrets=Secrets)
    context = Context(models)
    assert isinstance(context.options, Options)
    assert isinstance(context.config, Config)
    with patch("cli.get"):
        assert isinstance(context.secrets, Secrets)
