from dataclasses import dataclass

import dacite
import pytest
from hypothesis import given, strategies

from package_utils.dataclasses import SerializationMixin


@dataclass
class Model(SerializationMixin):
    message: str
    debug: bool = True
    verbosity: int = 0


@given(
    message=strategies.text(),
    debug=strategies.booleans(),
    verbosity=strategies.integers(),
)
def test_content_preserved(*, message: str, debug: bool, verbosity: int) -> None:
    info = {"message": message, "debug": debug, "verbosity": verbosity}
    model = Model.from_dict(info)
    assert model.dict() == info


@given(message=strategies.text())
def test_defaults(message: str) -> None:
    info = {"message": message}
    model = Model.from_dict(info)
    assert model.message == message
    assert model.debug == Model.debug
    assert model.verbosity == Model.verbosity


def test_missing_key_detected() -> None:
    with pytest.raises(dacite.exceptions.MissingValueError):
        Model.from_dict({})


def test_unexpected_key_detected() -> None:
    with pytest.raises(dacite.exceptions.UnexpectedDataError):
        Model.from_dict({"non existing key": ""})
