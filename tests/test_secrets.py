from importlib import import_module

import pytest

from tests.utils import forbid_imports


def test_env_secret_loads_without_subprocess_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = "package_utils.secrets_"
    forbid_imports(monkeypatch, "shlex", "subprocess", from_module=name)
    monkeypatch.setenv("MY_SECRET", "value")
    secrets_ = import_module(name)
    assert secrets_.load_secret("my secret") == "value"
