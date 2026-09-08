from collections.abc import Callable
from dataclasses import dataclass, field

import pytest
from package_dev_utils.tests.args import cli_args

from package_utils.cli.entry_point import invoke_from_cli_args


@dataclass
class VariableLengthTuple:
    numbers: tuple[int, ...] = ()


@dataclass
class Dictionary:
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class Function:
    hook: Callable[[int], str] = str


@cli_args("--help")
@pytest.mark.parametrize("class_", [VariableLengthTuple, Dictionary, Function])
def test_unsupported_annotation_rejected(class_: type) -> None:
    with pytest.raises(RuntimeError):
        invoke_from_cli_args(class_)
