from __future__ import annotations

from typing import TYPE_CHECKING, Any

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.schema import CreateColumn, CreateIndex

if TYPE_CHECKING:
    from .database import Database

# columns before the indexes that may cover them
ADDITIVE_OPERATIONS = ("add_column", "add_index")


def schema_diff(database: Database) -> list[Any]:
    """Alembic operations needed to bring the live database up to the registry.

    Empty list means the live schema matches the registered scopes. Only tables
    the registry owns are compared, so foreign tables sharing the database are
    ignored. Drives startup reconciliation and standalone drift checks.
    """
    tables = database.tables.metadata.tables

    def include_name(name: str | None, type_: str, _: Any) -> bool:
        return name in tables if type_ == "table" else True

    options = {"include_name": include_name}
    with database.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts=options)
        return list(compare_metadata(context, database.tables.metadata))


def reconcile_schema(database: Database) -> None:
    """Apply purely additive schema drift; refuse anything else.

    A new column is semantically a no-op — NULL reads back as the dataclass
    default — and `Database` creates missing tables up front, so new columns
    and indexes are all that can be pending. Any other operation needs data
    handling the registry cannot express: a standalone one-shot script.
    """
    operations = schema_diff(database)
    blocked = [
        operation
        for operation in operations
        if operation_name(operation) not in ADDITIVE_OPERATIONS
    ]
    if blocked:
        message = f"The live schema needs a one-shot migration script for: {blocked}"
        raise RuntimeError(message)
    ordered = sorted(operations, key=lambda op: ADDITIVE_OPERATIONS.index(op[0]))
    with database.transaction():
        for operation in ordered:
            apply_operation(database, operation)


def operation_name(operation: Any) -> str:
    # modify_* operations arrive grouped as a list of tuples
    return operation[0] if isinstance(operation[0], str) else operation[0][0]


def apply_operation(database: Database, operation: Any) -> None:
    if operation[0] == "add_column":
        column = CreateColumn(operation[3]).compile(dialect=database.engine.dialect)
        database.run(text(f"ALTER TABLE {operation[2]} ADD COLUMN {column}"))
    else:
        database.run(CreateIndex(operation[1]))
