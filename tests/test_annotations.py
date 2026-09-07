from collections.abc import Callable
from dataclasses import dataclass
from types import NoneType
from typing import Annotated, Literal, Optional, TypeVar

import pytest
from typing_extensions import TypeAliasType

from package_utils.annotations import (
    base_types_of,
    dataclass_of,
    first_parameter_types,
    resolve_aliases,
)

T = TypeVar("T")
ListAlias = TypeAliasType("ListAlias", list[T], type_params=(T,))
UnionAlias = TypeAliasType("UnionAlias", T | str, type_params=(T,))
IntListAlias = TypeAliasType("IntListAlias", list[int])
NoneAlias = TypeAliasType("NoneAlias", None)


@dataclass
class Options:
    debug: bool = False


def annotated_parameter(options: Annotated[Options, "metadata"]) -> None: ...


def optional_parameter(options: Options | None) -> None: ...


def no_parameters() -> None: ...


def unannotated_first_parameter(options, name: str) -> None:  # type: ignore[no-untyped-def]  # noqa: ANN001
    ...


def type_variable_parameter(options: T) -> None: ...


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
        (IntListAlias, [list]),
        (UnionAlias[int], [int, str]),
        (Literal["a", "b"], [str, str]),
        (Literal[1, "a"], [int, str]),
        (Literal["a"] | None, [str]),
        (Annotated[Literal[1], "metadata"], [int]),
        (T, []),
        (None, []),
        (NoneAlias, []),
        ("int", []),
    ],
)
def test_base_types_of(annotation: object, base_types: list[type]) -> None:
    assert list(base_types_of(annotation)) == base_types


@pytest.mark.parametrize(
    ("annotation", "resolution"),
    [
        (dict[str, ListAlias[int]], dict[str, list[int]]),
        (ListAlias[int] | None, list[int] | None),
        (Annotated[ListAlias[int], "metadata"], Annotated[list[int], "metadata"]),
    ],
)
def test_resolve_aliases(annotation: object, resolution: object) -> None:
    assert resolve_aliases(annotation) == resolution


@pytest.mark.parametrize(
    ("annotation", "dataclass_"),
    [
        (int | Options, Options),
        (list[Options], None),
    ],
)
def test_dataclass_of(annotation: object, dataclass_: type | None) -> None:
    assert dataclass_of(annotation) is dataclass_


@pytest.mark.parametrize(
    ("method", "types"),
    [
        (annotated_parameter, [Options]),
        (optional_parameter, [Options]),
        (no_parameters, []),
        (unannotated_first_parameter, []),
        (type_variable_parameter, []),
    ],
)
def test_first_parameter_types(
    method: Callable[..., None],
    types: list[type],
) -> None:
    assert list(first_parameter_types(method)) == types
