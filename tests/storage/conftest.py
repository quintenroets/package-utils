import pytest

from package_utils.storage import Database

from .fields import schema


@pytest.fixture
def db() -> Database:
    return Database(schema, path=":memory:")
