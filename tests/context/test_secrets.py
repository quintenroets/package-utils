import os
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from package_utils.context import Context
from tests.context.models.models import DefaultedSecrets, Secrets

if TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover
    from unittest.mock import MagicMock  # pragma: nocover


@pytest.fixture
def secrets() -> "Iterator[Secrets]":
    with create_secrets() as secrets_:
        yield secrets_


@contextmanager
def create_secrets(**environment: str) -> "Iterator[Secrets]":
    with patch.dict(os.environ, environment, clear=True):
        yield Context[None, None, Secrets](Secrets=Secrets).secrets


@patch("subprocess.check_output")
def test_askpass(check_output: "MagicMock") -> None:
    mock_value = "mock"
    check_output.return_value = f"{mock_value}\n".encode()
    with create_secrets(SECRET_ASKPASS="askpass") as secrets:  # noqa: S106
        assert secrets.token == mock_value


def test_missing_secret(secrets: Secrets) -> None:
    with pytest.raises(RuntimeError, match="TOKEN"):
        _ = secrets.token


def test_defaults(secrets: Secrets) -> None:
    assert secrets.defaulted.label == DefaultedSecrets.label


def test_default_factory() -> None:
    with create_secrets() as first, create_secrets() as second:
        assert first.defaulted.token != second.defaulted.token


def test_assigned(secrets: Secrets) -> None:
    injected = "injected"
    secrets.token = injected
    assert secrets.token == injected


def test_repr(secrets: Secrets) -> None:
    assert secrets.defaulted.label
    assert repr(secrets) == (
        "Secrets(token=<unresolved>, api=<unresolved>, optional_api=<unresolved>, "
        "defaulted=DefaultedSecrets(label=***, token=<unresolved>))"
    )


def test_hash(secrets: Secrets) -> None:
    hash(secrets.defaulted)
