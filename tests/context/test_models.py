from importlib import import_module

import pytest

from package_utils.context import Context
from tests.context.models import options_normal_class
from tests.context.models.models import Config, Options, Secrets
from tests.utils import forbid_imports, run_isolated


def test_empty_context() -> None:
    context = Context[None, None, None]()
    assert context.options is None
    assert context.config is None
    assert context.secrets is None


def test_options() -> None:
    context = Context[Options, None, None](Options=Options)
    assert isinstance(context.options, Options)
    assert context.options.debug == Options.debug
    assert context.options.config_path == Options.config_path
    assert context.config is None
    assert context.secrets is None


def test_config() -> None:
    context = Context[None, Config, None](Config=Config)
    assert isinstance(context.config, Config)
    assert context.config.output_path == Config.output_path
    assert context.options is None
    assert context.secrets is None


def test_secrets() -> None:
    context = Context[None, None, Secrets](Secrets=Secrets)
    assert isinstance(context.secrets, Secrets)
    assert context.options is None
    assert context.config is None


def test_full_context() -> None:
    context = Context(Options=Options, Config=Config, Secrets=Secrets)
    assert isinstance(context.options, Options)
    assert isinstance(context.config, Config)
    assert isinstance(context.secrets, Secrets)


def test_normal_class_options() -> None:
    context = Context[options_normal_class.Options, None, None](
        Options=options_normal_class.Options,
    )
    assert isinstance(context.options, options_normal_class.Options)
    assert context.config is None
    assert context.secrets is None


def test_import_without_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    name = "package_utils.context"
    forbid_imports(monkeypatch, "dacite", "superpathlib", from_module=name)
    context_module = import_module(name)
    context_module.Context[None, None, None]()


def test_missing_config_file_never_imports_dacite() -> None:
    """A config that is not there costs no more than constructing its defaults."""
    source = """
import sys
from package_utils.context import Context
from tests.context.models.models import Config, Options
context = Context[Options, Config, None](Options=Options, Config=Config)
assert context.config == Config()
assert "dacite" not in sys.modules, "a missing config file imported dacite"
"""
    run_isolated(source)


def test_import_costs_nothing_beyond_stdlib() -> None:
    """Each loader should cost its dependencies only once someone reaches for it."""
    source = """
import sys
from package_utils.context import Context
Context[None, None, None]()
assert "dacite" not in sys.modules, "importing the context imported dacite"
assert "superpathlib" not in sys.modules, "importing the context imported superpathlib"
"""
    run_isolated(source)
