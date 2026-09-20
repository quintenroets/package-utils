from importlib import import_module

import pytest

from tests.utils import forbid_imports


def test_loading_without_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    name = "package_utils.secrets_"
    forbid_imports(monkeypatch, "shlex", "subprocess", from_module=name)
    monkeypatch.setenv("MY_SECRET", "value")
    secrets_ = import_module(name)
    assert secrets_.load_secret("my secret") == "value"


from tests.utils import run_isolated


def test_loading_never_imports_dacite() -> None:
    """A secret is stdlib-only: nothing about it should pull the context machinery."""
    source = """
import sys
import os
from package_utils.secrets_ import load_secret
os.environ["MY_SECRET"] = "value"
assert load_secret("my secret") == "value"
assert "dacite" not in sys.modules, "reading a secret imported dacite"
assert "superpathlib" not in sys.modules, "reading a secret imported superpathlib"
"""
    run_isolated(source)
