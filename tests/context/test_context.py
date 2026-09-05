import os
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType
from typing import Any, cast
from unittest.mock import patch

import dacite
import pytest
from superpathlib import Path

from package_utils.context import Context as Context_
from tests.context.models import models, models_with_string_annotations

Context = Context_[models.Options, models.Config, models.Secrets]


@pytest.fixture(
    params=(models, models_with_string_annotations),
    ids=("resolved", "string_annotations"),
)
def models_(request: pytest.FixtureRequest) -> ModuleType:
    return cast("ModuleType", request.param)


@pytest.fixture
def context(models_: ModuleType) -> Context:
    return Context(models_.Options, models_.Config, models_.Secrets)


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
    config_values = {"output_path": str(output_path)}
    with filled_path(config_values) as config_path:
        context.options.config_path = config_path
        config = context.config
    assert config.output_path == output_path


def test_non_existing_config_value_detected(context: Context) -> None:
    expect_exception = pytest.raises(dacite.exceptions.UnexpectedDataError)
    config_values = {"non_existing": ""}
    with expect_exception, filled_path(config_values) as config_path:
        context.options.config_path = config_path
        _ = context.config


def test_secrets_from_environment(context: Context, models_: ModuleType) -> None:
    secrets = models_.Secrets("token", models_.ApiSecrets("id", "api_token"))
    environment_secrets = {
        "TOKEN": secrets.token,
        "API_ID": secrets.api.id,
        "API_TOKEN": secrets.api.token,
    }
    with patch.dict(os.environ, environment_secrets):
        assert context.secrets == secrets


def test_is_running_in_ci(context: Context) -> None:
    assert not context.is_running_in_ci
