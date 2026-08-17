import os
from unittest.mock import patch

import pytest

from package_utils.secrets_ import SecretLoader
from tests.utils import run_isolated

ABSENT_NAME = "my_nonexistent_secret_xyz"


def test_environment_variable() -> None:
    with patch.dict(os.environ, {ABSENT_NAME.upper(): "mock_value"}):
        assert SecretLoader(ABSENT_NAME).load() == "mock_value"


def test_askpass() -> None:
    with (
        patch.dict(os.environ, {"SECRET_ASKPASS": "/mock/pw"}),
        patch(
            "package_utils.secrets_.subprocess.check_output",
            return_value=b"mock_value",
        ),
    ):
        assert SecretLoader(ABSENT_NAME).load() == "mock_value"


def test_missing() -> None:
    with (
        patch.dict(os.environ, {"SECRET_ASKPASS": ""}),
        pytest.raises(RuntimeError, match=ABSENT_NAME),
    ):
        SecretLoader(ABSENT_NAME).load()


def test_loading_never_imports_dacite() -> None:
    """A secret is stdlib-only: nothing about it should pull the context machinery."""
    source = """
import sys
from package_utils.secrets_ import SecretLoader
import os
os.environ["MY_SECRET"] = "value"
assert SecretLoader("my secret").load() == "value"
assert "dacite" not in sys.modules, "reading a secret imported dacite"
assert "superpathlib" not in sys.modules, "reading a secret imported superpathlib"
"""
    run_isolated(source)
