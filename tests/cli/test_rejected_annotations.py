from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from package_dev_utils.tests.args import no_cli_args

from package_utils.cli import instantiate_from_cli_args


@dataclass
class VariableLengthTuple:
    numbers: tuple[int, ...] = ()


@dataclass
class Dictionary:
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class Function:
    hook: Callable[[int], str] = str


@no_cli_args
@pytest.mark.parametrize("class_", [VariableLengthTuple, Dictionary, Function])
def test_unsupported_annotation_rejected(class_: type) -> None:
    with pytest.raises(RuntimeError):
        instantiate_from_cli_args(class_)
