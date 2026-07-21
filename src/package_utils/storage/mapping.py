from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, TypeVar, cast

from .schema import (
    ATTR_DELIMITER,
    ChildSpec,
    RecordSpec,
    ScalarSpec,
    attr_field_type_map,
    nested_record_fields,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

T = TypeVar("T")


def element_from(spec: ChildSpec, row: Any) -> Any:
    element: Any
    if isinstance(spec, RecordSpec):
        element = instance_from(spec.cls, row)
    else:
        field_ = cast("ScalarSpec", spec).value_field
        value = row[field_.name]
        element = None if value is None else coerce(field_.type_, value)
    return element


def instances_from(cls: type[T], rows: Iterable[Any]) -> list[T]:
    return [instance_from(cls, row) for row in rows]


def instance_from(cls: type[T], row: Any) -> T:
    data: dict[str, Any] = {}
    for attr, (field_, base_type) in attr_field_type_map(cls).items():
        value = row[field_.name]
        if value is not None:
            assign_path(data, attr, coerce(base_type, value))
    return construct(cls, data)


def construct(cls: type[T], data: dict[str, Any]) -> T:
    """Build the dataclass from a nested dict of column values.

    Absent keys (a NULL column, an all-NULL nested record) fall through to the
    dataclass's own defaults. Nested records arrive as sub-dicts that recurse.
    """
    for attr, record_cls in nested_record_fields(cls).items():
        if attr in data:
            data[attr] = construct(record_cls, data[attr])
    return cls(**data)


def coerce(base_type: type, value: Any) -> Any:
    """Normalize a column value to its Python type.

    Idempotent: Core already types rows from `select()`, but raw `text()` SQL
    yields DBAPI-native scalars (a bool as `0`, a datetime as an ISO string),
    so the escape-hatch path goes through this too.
    """
    result: Any
    if base_type is bool:
        result = bool(value)
    elif base_type is datetime and isinstance(value, str):
        result = datetime.fromisoformat(value)
    elif base_type is date and isinstance(value, str):
        result = date.fromisoformat(value)
    elif is_enum_name(base_type, value):
        result = cast("Any", base_type)[value]
    else:
        result = value
    return result


def is_enum_name(base_type: type, value: Any) -> bool:
    is_enum = isinstance(base_type, type) and issubclass(base_type, Enum)
    return is_enum and isinstance(value, str)


def assign_path(data: dict[str, Any], path: str, value: Any) -> None:
    *parents, leaf = path.split(ATTR_DELIMITER)
    for parent in parents:
        data = data.setdefault(parent, {})
    data[leaf] = value
