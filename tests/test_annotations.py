from collections.abc import Callable
from dataclasses import dataclass
from types import NoneType, SimpleNamespace
from typing import Annotated, Literal, Optional

import pytest

from package_utils.annotations import base_types_of, first_parameter_types

type_alias = SimpleNamespace(__value__=list[int])


@dataclass
class Options:
    debug: bool = False


def annotated_parameter(options: Annotated[Options, "metadata"]) -> None: ...


def optional_parameter(options: Options | None) -> None: ...


def no_parameters() -> None: ...


def unannotated_first_parameter(options, name: str) -> None:  # type: ignore[no-untyped-def]  # noqa: ANN001
    ...


@pytest.mark.parametrize(
    ("annotation", "base_types"),
    [
        (int, [int]),
        (list[int], [list]),
        (int | str, [int, str]),
        (Optional[int], [int]),  # noqa: UP045
        (tuple[int, str] | None, [tuple]),
        (NoneType, [NoneType]),
        (Annotated[int, "metadata"], [int]),
        (type_alias, [list]),
        (Literal["a", "b"], [str, str]),
        (Literal[1, "a"], [int, str]),
        (Literal["a"] | None, [str]),
        (Annotated[Literal[1], "metadata"], [int]),
    ],
)
def test_base_types_of(annotation: object, base_types: list[type]) -> None:
    assert list(base_types_of(annotation)) == base_types


@pytest.mark.parametrize(
    ("method", "types"),
    [
        (annotated_parameter, [Options]),
        (optional_parameter, [Options]),
        (no_parameters, []),
        (unannotated_first_parameter, []),
    ],
)
def test_first_parameter_types(
    method: Callable[..., None],
    types: list[type],
) -> None:
    assert list(first_parameter_types(method)) == types
