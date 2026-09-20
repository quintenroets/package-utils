from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from functools import partial
from typing import TYPE_CHECKING, Any, NamedTuple, TypeVar, cast

from .schema import (
    ATTR_DELIMITER,
    ChildSpec,
    RecordSpec,
    ScalarSpec,
    attr_field_map,
    nested_record_fields,
    typed_cache,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence

    Converter = Callable[[Any], Any]
    Reader = Callable[[Any], Any]

T = TypeVar("T")


def instances_from(cls: type[T], rows: Iterable[Any]) -> list[T]:
    """Map rows from hand-written SQL, whose column order the caller owns.

    Reads by name through each row's mapping view, so the projection may list
    the columns in any order; the `Store` path reads by index instead.
    """
    read = record_plan(cls).instance
    return [cast("T", read(row._mapping)) for row in rows]  # noqa: SLF001


def element_reader(spec: ChildSpec, order: Sequence[str]) -> Reader:
    """Resolve a child spec to the function that maps one row to one element.

    `order` is the projection's column names; binding each column to its index
    keeps the spec dispatch, the name lookups and the per-type conversions out
    of the per-row path.
    """
    index_of = {name: index for index, name in enumerate(order)}
    if isinstance(spec, RecordSpec):
        read: Reader = record_plan(spec.cls).indexed(index_of).instance
    else:
        field_ = cast("ScalarSpec", spec).value_field
        convert = converter_for(field_.type_)
        read = partial(scalar_from, index_of[field_.name], convert)
    return read


def scalar_from(key: Any, convert: Converter | None, row: Any) -> Any:
    value = row[key]
    return value if value is None or convert is None else convert(value)


class FieldPlan(NamedTuple):
    """A single column, resolved to where it lands and how it converts.

    `key` reads the value out of a row — a column name against a mapping view,
    or a position once `RecordPlan.indexed` has bound it to a projection. A
    tuple rather than a dataclass so the per-row loop unpacks it in one step.
    """

    attr: str
    key: Any
    convert: Converter | None


@dataclass(frozen=True)
class RecordPlan:
    """How to build one instance of `cls` from a row, resolved once per class."""

    cls: type
    fields: tuple[FieldPlan, ...]
    nested: tuple[tuple[str, RecordPlan], ...]

    def indexed(self, index_of: dict[str, int]) -> RecordPlan:
        """The same plan with every column bound to its position in a projection."""
        fields = tuple(
            FieldPlan(attr, index_of[key], convert)
            for attr, key, convert in self.fields
        )
        nested = tuple((attr, plan.indexed(index_of)) for attr, plan in self.nested)
        return RecordPlan(self.cls, fields, nested)

    def instance(self, row: Any) -> Any:
        return self.cls(**self.values(row))

    def values(self, row: Any) -> dict[str, Any]:
        """Constructor arguments for one row, keyed by attribute.

        A NULL column (and a nested record whose columns are all NULL) is left
        out so the dataclass's own default fills it in — that is how a column
        added by additive schema drift reads back on rows predating it.
        """
        values: dict[str, Any] = {}
        for attr, key, convert in self.fields:
            value = row[key]
            if value is not None:
                values[attr] = value if convert is None else convert(value)
        for attr, plan in self.nested:
            nested_values = plan.values(row)
            if nested_values:
                values[attr] = plan.cls(**nested_values)
        return values


@typed_cache
def record_plan(cls: type) -> RecordPlan:
    nested = tuple(
        (attr, record_plan(record_cls))
        for attr, record_cls in nested_record_fields(cls).items()
    )
    return RecordPlan(cls, tuple(field_plans(cls)), nested)


def field_plans(cls: type) -> Iterator[FieldPlan]:
    for attr, field_ in attr_field_map(cls).items():
        # a delimiter marks a nested record's column; `nested` recurses into those
        if ATTR_DELIMITER not in attr:
            yield FieldPlan(attr, field_.name, converter_for(field_.type_))


def converter_for(base_type: type) -> Converter | None:
    """The normalization a column of this type needs, or None when it needs none.

    Core already types rows from `select()`, but raw `text()` SQL yields DBAPI-native
    scalars (a bool as `0`, a datetime as an ISO string), so the escape-hatch path
    goes through these too. Each stays idempotent for the already-typed case.
    """
    convert: Converter | None
    if base_type is bool:
        convert = bool
    elif base_type is datetime:
        convert = parse_datetime
    elif base_type is date:
        convert = parse_date
    elif isinstance(base_type, type) and issubclass(base_type, Enum):
        convert = partial(enum_member, base_type)
    else:
        convert = None
    return convert


def parse_datetime(value: Any) -> Any:
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def parse_date(value: Any) -> Any:
    return date.fromisoformat(value) if isinstance(value, str) else value


def enum_member(enum: type, value: Any) -> Any:
    return cast("Any", enum)[value] if isinstance(value, str) else value


def assign_path(data: dict[str, Any], path: str, value: Any) -> None:
    *parents, leaf = path.split(ATTR_DELIMITER)
    for parent in parents:
        data = data.setdefault(parent, {})
    data[leaf] = value
