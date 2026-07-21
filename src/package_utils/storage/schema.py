from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, is_dataclass
from functools import cache
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ParamSpec,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

P = ParamSpec("P")
R = TypeVar("R")

DELIMITER = "_"
ATTR_DELIMITER = "."
UNSET_TYPE: type = cast("type", None)


def typed_cache(func: Callable[P, R]) -> Callable[P, R]:
    return cast("Callable[P, R]", cache(func))


@dataclass(eq=False)
class Field:
    type_: type = UNSET_TYPE
    name: str = ""


class Key(Field):
    pass


@dataclass(frozen=True)
class ChildSpec(ABC):
    """A collection-valued attribute mapped to a child scope.

    `keyed` distinguishes a dict (own key is the mapping key) from a list (own
    key is the positional index). `RecordSpec` maps a dataclass element to a
    scope; `ScalarSpec` maps a scalar element to a single value column. A
    top-level read/write of a whole scope uses an attr-less spec (`attr=""`).
    """

    attr: str
    keyed: bool

    def collection_items(self, collection: Any) -> Any:
        return collection.items() if self.keyed else enumerate(collection)

    @abstractmethod
    def scope_of(self, schema: Schema) -> Scope: ...

    @abstractmethod
    def grandchildren(self) -> tuple[ChildSpec, ...]: ...

    @abstractmethod
    def column_names(self) -> list[str]: ...

    @abstractmethod
    def value_columns(self, element: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RecordSpec(ChildSpec):
    cls: type

    def scope_of(self, schema: Schema) -> Scope:
        return schema.scope_of_dataclass(self.cls)

    def grandchildren(self) -> tuple[ChildSpec, ...]:
        return child_specs(self.cls)

    def column_names(self) -> list[str]:
        return [field_.name for field_, _ in attr_field_type_map(self.cls).values()]

    def value_columns(self, element: Any) -> dict[str, Any]:
        return {
            field_.name: resolve_attr(element, attr)
            for attr, (field_, _) in attr_field_type_map(self.cls).items()
            if not isinstance(field_, Key)
        }


@dataclass(frozen=True)
class ScalarSpec(ChildSpec):
    value_field: Field

    def scope_of(self, schema: Schema) -> Scope:
        return schema.scope_of_field(self.value_field)

    def grandchildren(self) -> tuple[ChildSpec, ...]:
        return ()

    def column_names(self) -> list[str]:
        return [self.value_field.name]

    def value_columns(self, element: Any) -> dict[str, Any]:
        return {self.value_field.name: element}


@dataclass(frozen=True)
class Scope:
    table: str
    key_columns: tuple[Field, ...] = ()
    fields: tuple[Field, ...] = ()
    parent: Scope | None = None

    @property
    def singleton(self) -> bool:
        return not self.key_columns and self.parent is None


def base_type_of(annotation: Any) -> type:
    origin = get_origin(annotation)
    if origin is UnionType or origin is Union:
        members = (arg for arg in get_args(annotation) if arg is not type(None))
        result = base_type_of(next(members, annotation))
    elif origin is None:
        result = annotation
    else:
        result = cast("type", origin)
    return result


def is_field_spec(spec: Any) -> bool:
    return get_origin(spec) is Annotated


def field_of(annotation: Any) -> Field | None:
    candidates = (resolve_field(meta) for meta in get_args(annotation)[1:])
    return next((field_ for field_ in candidates if field_ is not None), None)


def resolve_attr(instance: Any, path: str) -> Any:
    for attr in path.split(ATTR_DELIMITER):
        instance = getattr(instance, attr)
    return instance


def resolve_field(meta: Any) -> Field | None:
    field_: Field | None
    if isinstance(meta, Field):
        field_ = meta
    elif get_origin(meta) is Annotated:
        field_ = field_of(meta)
    else:
        field_ = None
    return field_


def assign_names(namespace: type, prefix: str = "") -> Iterator[Field]:
    for attr, value in vars(namespace).items():
        if get_origin(value) is Annotated:
            field_ = field_of(value)
            if field_ is not None:
                field_.name = f"{prefix}{attr}"
                field_.type_ = base_type_of(get_args(value)[0])
                yield field_
        elif isinstance(value, type) and not attr.startswith("__"):
            yield from assign_names(value, f"{prefix}{attr}{DELIMITER}")


def inherited_keys(parent: Scope | None) -> tuple[Field, ...]:
    if parent is None:
        return ()
    inherited_count = len(parent.parent.key_columns) if parent.parent else 0
    ancestors = parent.key_columns[:inherited_count]
    own = parent.key_columns[inherited_count:]
    copied = (Field(field_.type_, field_.name) for field_ in ancestors)
    renamed = (
        Field(field_.type_, f"{parent.table}{DELIMITER}{field_.name}") for field_ in own
    )
    return (*copied, *renamed)


@dataclass(frozen=True)
class Index:
    scope: Scope
    columns: tuple[Field, ...]
    where: str = ""
    unique: bool = False

    @property
    def name(self) -> str:
        column_names = DELIMITER.join(field_.name for field_ in self.columns)
        return f"ix{DELIMITER}{self.scope.table}{DELIMITER}{column_names}"


@dataclass(frozen=True)
class Check:
    scope: Scope
    predicate: str


@dataclass
class Schema:
    scopes: list[Scope] = field(default_factory=list)
    field_scopes: dict[Field, Scope] = field(default_factory=dict)
    column_types: dict[type, Any] = field(default_factory=dict)
    indexes: list[Index] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)

    def register_column_type(self, type_: type, sql_type: Any) -> None:
        """Plug a consumer SQLAlchemy column type in for `type_`.

        Same mechanism the built-in `IsoDateTime`/`IsoDate` decorators use, but
        consumer-supplied — e.g. keybias registers a `NumpyArray(TypeDecorator)`
        so numpy stays out of the library. `sql_type` is a SQLAlchemy
        `TypeEngine` instance, kept as `Any` so this module imports no SQLAlchemy.
        """
        self.column_types[type_] = sql_type

    def scope(self, namespace: type, parent: Scope | None = None) -> Scope:
        all_fields = list(assign_names(namespace))
        keys = tuple(f for f in all_fields if isinstance(f, Key))
        fields = tuple(f for f in all_fields if not isinstance(f, Key))
        keyed = bool(keys) or parent is not None
        key_columns = (*inherited_keys(parent), *keys) if keyed else ()
        scope = Scope(namespace.__name__, key_columns, fields, parent)
        self.scopes.append(scope)
        self.field_scopes.update(
            dict.fromkeys((*scope.key_columns, *scope.fields), scope),
        )
        return scope

    def index(self, *specs: Any, where: str = "", unique: bool = False) -> None:
        columns = tuple(cast("Field", field_of(spec)) for spec in specs)
        scope = self.scope_of_field(columns[0])
        self.indexes.append(Index(scope, columns, where, unique))

    def check(self, scope: Scope, predicate: str) -> None:
        self.checks.append(Check(scope, predicate))

    def column(self, spec: Any) -> str:
        return cast("Field", field_of(spec)).name

    def table_of(self, cls: type) -> str:
        return self.scope_of_dataclass(cls).table

    def scope_of_field(self, field_: Field) -> Scope:
        return self.field_scopes[field_]

    def scope_of_dataclass(self, cls: type) -> Scope:
        fields = attr_field_type_map(cls)
        if fields:
            scope = self.scope_of_field(next(iter(fields.values()))[0])
        else:
            scope = cast("Scope", child_specs(cls)[0].scope_of(self).parent)
        return scope


@typed_cache
def child_specs(cls: type) -> tuple[ChildSpec, ...]:
    hints = get_type_hints(cls, include_extras=True)
    specs = (child_spec_of(attr, hint) for attr, hint in hints.items())
    return tuple(spec for spec in specs if spec is not None)


def child_spec_of(attr: str, hint: Any) -> ChildSpec | None:
    value_field = field_of(hint) if is_field_spec(hint) else None
    annotation = get_args(hint)[0] if value_field is not None else hint
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is list:
        spec = collection_spec(attr, keyed=False, element=args[0], value=value_field)
    elif origin is dict:
        spec = collection_spec(attr, keyed=True, element=args[1], value=value_field)
    else:
        spec = None
    return spec


def collection_spec(
    attr: str,
    *,
    keyed: bool,
    element: Any,
    value: Field | None,
) -> ChildSpec | None:
    if is_dataclass(element):
        spec: ChildSpec | None = RecordSpec(attr, keyed, cast("type", element))
    elif value is not None:
        spec = ScalarSpec(attr, keyed, value)
    else:
        spec = None
    return spec


@typed_cache
def nested_record_fields(cls: type) -> dict[str, type]:
    hints = get_type_hints(cls)
    return {
        attr: cast("type", hint) for attr, hint in hints.items() if is_dataclass(hint)
    }


@typed_cache
def attr_field_type_map(cls: type, prefix: str = "") -> dict[str, tuple[Field, type]]:
    hints = get_type_hints(cls, include_extras=True)
    result: dict[str, tuple[Field, type]] = {}
    for attr_name, hint in hints.items():
        path = f"{prefix}{attr_name}"
        if is_dataclass(hint):
            nested = cast("type", hint)
            result.update(attr_field_type_map(nested, f"{path}{ATTR_DELIMITER}"))
        elif get_origin(hint) is Annotated:
            inner = get_args(hint)[0]
            field_ = field_of(hint)
            if field_ is not None and get_origin(inner) not in (list, dict):
                result[path] = (field_, base_type_of(inner))
    return result
