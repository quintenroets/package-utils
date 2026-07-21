from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    MetaData,
    Table,
    Text,
    TypeDecorator,
    text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Index as SqlIndex
from sqlalchemy.schema import CreateIndex, CreateTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine import Dialect, Engine

    from .schema import Index, Schema, Scope


class IsoDateTime(TypeDecorator[datetime]):
    """SQLite stores datetimes as ISO text so the timezone survives the round trip."""

    impl = Text
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> str | None:
        return None if value is None else value.isoformat()

    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> datetime | None:
        return None if value is None else datetime.fromisoformat(value)


class IsoDate(TypeDecorator[date]):
    impl = Text
    cache_ok = True

    def process_bind_param(
        self,
        value: date | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> str | None:
        return None if value is None else value.isoformat()

    def process_result_value(
        self,
        value: str | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> date | None:
        return None if value is None else date.fromisoformat(value)


COLUMN_TYPES: dict[type, Any] = {
    int: Integer(),
    float: Float(),
    str: Text(),
    bytes: LargeBinary(),
    bool: Boolean(),
    datetime: DateTime(timezone=True).with_variant(IsoDateTime(), "sqlite"),
    date: Date().with_variant(IsoDate(), "sqlite"),
}


def column_type(type_: type, registered: dict[type, Any]) -> Any:
    if type_ in registered:
        result = registered[type_]
    elif issubclass(type_, Enum):
        result = SqlEnum(type_)
    else:
        result = COLUMN_TYPES[type_]
    return result


@dataclass(frozen=True)
class SchemaTables:
    metadata: MetaData
    tables: dict[Scope, Table]

    def table_of(self, scope: Scope) -> Table:
        return self.tables[scope]

    def fingerprint(self, engine: Engine) -> int:
        """31-bit digest of the compiled DDL; fits SQLite's `user_version` slot."""
        ddl = "\n".join(compile_ddl(self.metadata, engine.dialect))
        return int.from_bytes(sha256(ddl.encode()).digest()[:4]) & 0x7FFFFFFF


def compile_ddl(metadata: MetaData, dialect: Dialect) -> Iterator[str]:
    for table in metadata.tables.values():
        yield str(CreateTable(table).compile(dialect=dialect))
        for index in sorted(table.indexes, key=lambda i: cast("str", i.name)):
            yield str(CreateIndex(index).compile(dialect=dialect))


def build_tables(schema: Schema) -> SchemaTables:
    metadata = MetaData()
    types = schema.column_types
    tables = {scope: build_table(scope, metadata, types) for scope in schema.scopes}
    for index in schema.indexes:
        build_index(index, tables)
    for check in schema.checks:
        tables[check.scope].append_constraint(CheckConstraint(check.predicate))
    return SchemaTables(metadata, tables)


def build_index(index: Index, tables: dict[Scope, Table]) -> None:
    table = tables[index.scope]
    columns = [table.c[field_.name] for field_ in index.columns]
    options: dict[str, Any] = {"unique": index.unique}
    if index.where:
        predicate = text(index.where)
        options["sqlite_where"] = predicate
        options["postgresql_where"] = predicate
    SqlIndex(index.name, *columns, **options)


def build_table(scope: Scope, metadata: MetaData, types: dict[type, Any]) -> Table:
    members = (*scope_columns(scope, types), *scope_constraints(scope))
    return Table(scope.table, metadata, *members)


def scope_columns(scope: Scope, types: dict[type, Any]) -> Iterator[Column[Any]]:
    if scope.singleton:
        yield Column("id", Integer, primary_key=True, default=1)
    else:
        for field_ in scope.key_columns:
            yield Column(
                field_.name,
                column_type(field_.type_, types),
                primary_key=True,
                nullable=False,
            )
    for field_ in scope.fields:
        yield Column(field_.name, column_type(field_.type_, types))


def scope_constraints(scope: Scope) -> Iterator[Any]:
    if scope.singleton:
        yield CheckConstraint("id = 1")
    if scope.parent is not None:
        parent = scope.parent
        local = [field_.name for field_ in scope.key_columns[: len(parent.key_columns)]]
        remote = [f"{parent.table}.{field_.name}" for field_ in parent.key_columns]
        yield ForeignKeyConstraint(local, remote, ondelete="CASCADE")
