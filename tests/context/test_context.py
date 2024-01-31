import os
import typing
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import dacite
import pytest
from package_utils.context import Context as Context_
from plib import Path

from tests.context.models.config import Config
from tests.context.models.options import Options
from tests.context.models.secrets_ import Secrets

NestedDict = dict[str, str | dict[str, str]]


Context = Context_[Options, Config, Secrets]


@pytest.fixture
def context() -> Context:
    return Context(Options, Config, Secrets)


@contextmanager
def filled_path(values: dict[str, Any]) -> Iterator[Path]:
    path = Path.tempfile()
    path.yaml = values
    try:
        yield path
    finally:
        path.unlink()


def test_specified_config(context: Context) -> None:
    output_path = Path.tempfile(create=False)
    secrets_path = Path.tempfile(create=False)
    config_values = {
        "output_path": str(output_path),
        "secrets_path": str(secrets_path),
    }
    with filled_path(config_values) as config_path:
        context.options.config_path = config_path
        config = context.config
    assert config.output_path == output_path
    assert config.secrets_path == secrets_path


def test_non_existing_config_value_detected(context: Context) -> None:
    expect_exception = pytest.raises(dacite.exceptions.UnexpectedDataError)
    config_values = {"non_existing": ""}
    with expect_exception, filled_path(config_values) as config_path:
        context.options.config_path = config_path
        _ = context.config


@pytest.fixture
def secrets() -> NestedDict:
    api_secrets = {"id": "id", "token": "api_token"}
    return {"token": "token", "api": api_secrets}


def test_secrets_from_file(context: Context, secrets: NestedDict) -> None:
    with filled_path(secrets) as secrets_path:
        context.config.secrets_path = secrets_path
        verify_secret_values(context, secrets)


def verify_secret_values(context: Context, secrets: NestedDict) -> None:
    api_secrets = typing.cast(dict[str, str], secrets["api"])
    assert context.secrets.token == secrets["token"]
    assert context.secrets.api.id == api_secrets["id"]
    assert context.secrets.api.token == api_secrets["token"]


@pytest.fixture
def environment_secrets() -> dict[str, str]:
    return {"token": "token", "api_id": "id", "api_token": "api_token"}


@contextmanager
def secrets_in_environment(secrets: dict[str, str]) -> Iterator[None]:
    for k, v in secrets.items():
        os.environ[k] = v
    yield
    for k in secrets:
        os.environ.pop(k)


def test_secrets_from_environment(
    context: Context, secrets: NestedDict, environment_secrets: dict[str, str]
) -> None:
    with secrets_in_environment(environment_secrets):
        verify_secret_values(context, secrets)


def test_secrets_from_environment_and_file(
    context: Context, secrets: NestedDict
) -> None:
    token = secrets.pop("token")
    environment_secrets = {"token": typing.cast(str, token)}
    filled_secrets_path = filled_path(secrets)
    environment_with_secrets = secrets_in_environment(environment_secrets)
    with filled_secrets_path as secrets_path, environment_with_secrets:
        context.config.secrets_path = secrets_path
        combined_secrets = secrets | environment_secrets
        verify_secret_values(context, combined_secrets)


def test_secrets_from_command(
    context: Context, environment_secrets: dict[str, str], secrets: NestedDict
) -> None:
    filled_secrets_path = filled_path({})
    patched_command = patch("cli.get", new=lambda _, key: os.environ[key])
    environment_with_secrets = secrets_in_environment(environment_secrets)
    with filled_secrets_path as secrets_path, environment_with_secrets, patched_command:
        context.config.secrets_path = secrets_path
        verify_secret_values(context, secrets)
