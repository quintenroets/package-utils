from __future__ import annotations

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    cast,
    overload,
)

from sqlalchemy import and_, delete, insert, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .mapping import element_from
from .schema import (
    ChildSpec,
    Field,
    Key,
    RecordSpec,
    ScalarSpec,
    attr_field_type_map,
    field_of,
    is_field_spec,
    resolve_attr,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from .database import Database
    from .schema import Scope

UPSERT_INSERT = {"sqlite": sqlite_insert, "postgresql": postgres_insert}

KeyPair = tuple[str, Any]


@dataclass(frozen=True)
class Store:
    database: Database
    keys: tuple[Any, ...] = ()

    def __getitem__(self, key: Any) -> Store:
        return Store(self.database, (*self.keys, key))

    def transaction(self) -> AbstractContextManager[None]:
        return self.database.transaction()

    @overload
    def read(self, spec: type[T]) -> T | None: ...
    @overload
    def read(self, spec: Any) -> Any: ...
    def read(self, spec: Any) -> Any:
        child = read_spec(spec)
        scope = child.scope_of(self.database.schema)
        table = self.database.table_of(scope)
        columns = [table.c[name] for name in child.column_names()]
        statement = self._filter(select(*columns), scope, exact=True)
        row = self.database.fetch_one(statement)
        return self._element_of(child, row)

    def _element_of(self, spec: ChildSpec, row: Any) -> Any:
        if row is None:
            element = None
        else:
            element = element_from(spec, row)
            self._attach_children(spec, {(): element})
        return element

    @overload
    def write(self, spec: type[T], value: T | None) -> None: ...
    @overload
    def write(self, spec: Any, value: Any) -> None: ...
    @overload
    def write(self, spec: object) -> None: ...
    def write(self, spec: Any, value: Any = None) -> None:
        if is_field_spec(spec):
            field_ = cast("Field", field_of(spec))
            scope = self.database.schema.scope_of_field(field_)
            self._upsert(scope, {field_.name: value})
        else:
            self._write_instance(spec)

    def _write_instance(self, instance: Any) -> None:
        spec = record_spec(type(instance))
        scope = spec.scope_of(self.database.schema)
        covered = len(self._key_pairs(scope))
        instance_keys = [
            resolve_attr(instance, attr)
            for attr, (field_, _) in attr_field_type_map(type(instance)).items()
            if isinstance(field_, Key)
        ]
        store = self
        for key in instance_keys[covered:]:
            store = store[key]
        with self.database.transaction():
            store._upsert(scope, spec.value_columns(instance))  # noqa: SLF001
            for child in spec.grandchildren():
                store._delete_scope(child)  # noqa: SLF001
                store._insert_collection(child, getattr(instance, child.attr))  # noqa: SLF001

    def read_or_default(self, cls: type[T]) -> T:
        result = self.read(cls)
        return cls() if result is None else result

    @overload
    def read_list(self, spec: type[T]) -> list[T]: ...
    @overload
    def read_list(self, spec: Any) -> list[Any]: ...
    def read_list(self, spec: Any) -> list[Any]:
        return list(self._read_scope(read_spec(spec)).values())

    @overload
    def read_dict(self, spec: type[T]) -> dict[Any, T]: ...
    @overload
    def read_dict(self, spec: Any) -> dict[Any, Any]: ...
    def read_dict(self, spec: Any) -> dict[Any, Any]:
        elements = self._read_scope(read_spec(spec))
        return {
            key[0] if len(key) == 1 else key: element
            for key, element in elements.items()
        }

    def write_dict(self, spec: Any, mapping: dict[Any, Any]) -> None:
        self._replace_scope(write_spec(spec, keyed=True), mapping)

    def write_list(self, spec: Any, values: list[Any]) -> None:
        self._replace_scope(write_spec(spec, keyed=False), values)

    def _replace_scope(self, spec: ChildSpec, collection: Any) -> None:
        with self.database.transaction():
            self._delete_scope(spec)
            self._insert_collection(spec, collection)

    def insert_list(self, instances: list[Any]) -> None:
        if instances:
            self._insert_collection(record_spec(type(instances[0])), instances)

    def _insert_collection(self, spec: ChildSpec, collection: Any) -> None:
        keyed = [
            ((*self.keys, key), element)
            for key, element in spec.collection_items(collection)
        ]
        self._insert_level(spec, keyed)

    def _insert_level(
        self,
        spec: ChildSpec,
        keyed: list[tuple[tuple[Any, ...], Any]],
    ) -> None:
        if keyed:
            scope = spec.scope_of(self.database.schema)
            table = self.database.table_of(scope)
            key_names = [field_.name for field_ in scope.key_columns]
            rows = [
                {
                    **dict(zip(key_names, key, strict=True)),
                    **spec.value_columns(element),
                }
                for key, element in keyed
            ]
            self.database.run_many(insert(table), rows)
            for child in spec.grandchildren():
                self._insert_level(
                    child,
                    [
                        ((*key, child_key), child_element)
                        for key, element in keyed
                        for child_key, child_element in child.collection_items(
                            getattr(element, child.attr),
                        )
                    ],
                )

    def delete(self, cls: type) -> None:
        self._delete_scope(record_spec(cls))

    def _delete_scope(self, spec: ChildSpec) -> None:
        scope = spec.scope_of(self.database.schema)
        table = self.database.table_of(scope)
        self.database.run(self._filter(delete(table), scope, exact=False))

    def _read_scope(self, spec: ChildSpec) -> dict[tuple[Any, ...], Any]:
        scope = spec.scope_of(self.database.schema)
        table = self.database.table_of(scope)
        remaining = scope.key_columns[len(self._key_pairs(scope)) :]
        statement = self._filter(select(table), scope, exact=False)
        if remaining:
            statement = statement.order_by(*(table.c[k.name] for k in remaining))
        rows = self.database.fetch_all(statement)
        elements = {
            tuple(row[field_.name] for field_ in remaining): element_from(spec, row)
            for row in rows
        }
        self._attach_children(spec, elements)
        return elements

    def _attach_children(
        self,
        spec: ChildSpec,
        elements: dict[tuple[Any, ...], Any],
    ) -> None:
        for child in spec.grandchildren():
            children = self._read_scope(child)
            for key, child_element in children.items():
                container = getattr(elements[key[:-1]], child.attr)
                if child.keyed:
                    container[key[-1]] = child_element
                else:
                    container.append(child_element)

    def _upsert(self, scope: Scope, values: dict[str, Any]) -> None:
        table = self.database.table_of(scope)
        pairs = self._exact_key_pairs(scope)
        insert_ = UPSERT_INSERT[self.database.dialect_name]
        index_elements = [name for name, _ in pairs]
        statement: Any = insert_(table).values(**dict(pairs), **values)
        statement = (
            statement.on_conflict_do_update(index_elements=index_elements, set_=values)
            if values
            else statement.on_conflict_do_nothing(index_elements=index_elements)
        )
        self.database.run(statement)

    def _filter(self, statement: Any, scope: Scope, *, exact: bool) -> Any:
        table = self.database.table_of(scope)
        pairs = self._exact_key_pairs(scope) if exact else self._key_pairs(scope)
        conditions = [table.c[name] == value for name, value in pairs]
        return statement.where(and_(*conditions)) if conditions else statement

    def _exact_key_pairs(self, scope: Scope) -> list[KeyPair]:
        if not scope.singleton and len(self.keys) < len(scope.key_columns):
            message = f"A single-row operation on {scope.table} requires its full key"
            raise ValueError(message)
        return self._key_pairs(scope)

    def _key_pairs(self, scope: Scope) -> list[KeyPair]:
        if scope.singleton:
            pairs = [("id", 1)]
        else:
            names = [field_.name for field_ in scope.key_columns]
            pairs = list(zip(names, self.keys, strict=False))
        return pairs


def record_spec(cls: type) -> ChildSpec:
    return RecordSpec(attr="", keyed=False, cls=cls)


def scalar_spec(field_: Field, *, keyed: bool = False) -> ChildSpec:
    return ScalarSpec(attr="", keyed=keyed, value_field=field_)


def read_spec(spec: Any) -> ChildSpec:
    return (
        scalar_spec(cast("Field", field_of(spec)))
        if is_field_spec(spec)
        else record_spec(spec)
    )


def write_spec(spec: Any, *, keyed: bool) -> ChildSpec:
    return scalar_spec(cast("Field", field_of(spec)), keyed=keyed)
