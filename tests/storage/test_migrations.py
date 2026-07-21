from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

import pytest
from sqlalchemy import text

import package_utils.storage
from package_utils.storage import Database, Field, Key, Schema, Store, schema_diff

from .fields import schema

if TYPE_CHECKING:
    from pathlib import Path


def widget_registry(namespace: type) -> Schema:
    registry = Schema()
    registry.scope(namespace)
    return registry


class Version1:
    class widget:  # noqa: N801
        key = Annotated[str, Key()]
        name = Annotated[str, Field()]


class Version2:
    class widget:  # noqa: N801
        key = Annotated[str, Key()]
        name = Annotated[str, Field()]
        count = Annotated[int, Field()]


def test_unknown_attribute_raises() -> None:
    with pytest.raises(AttributeError):
        _ = package_utils.storage.does_not_exist


def test_a_new_column_is_reconciled_on_startup(tmp_path: Path) -> None:
    path = str(tmp_path / "data.db")
    database = Database(widget_registry(Version1.widget), path=path)
    Store(database)["a"].write(Version1.widget.name, "x")
    upgraded = Database(widget_registry(Version2.widget), path=path)
    assert Store(upgraded)["a"].read(Version2.widget.name) == "x"
    assert Store(upgraded)["a"].read(Version2.widget.count) is None


def test_a_new_index_is_reconciled_on_startup(tmp_path: Path) -> None:
    path = str(tmp_path / "data.db")
    Database(widget_registry(Version1.widget), path=path)
    indexed = widget_registry(Version2.widget)
    indexed.index(Version2.widget.name)
    database = Database(indexed, path=path)
    names_query = text("SELECT name FROM sqlite_master WHERE type = 'index'")
    names = [row["name"] for row in database.fetch_all(names_query)]
    assert "ix_widget_name" in names


def test_non_additive_drift_raises(tmp_path: Path) -> None:
    path = str(tmp_path / "data.db")
    Database(widget_registry(Version2.widget), path=path)
    with pytest.raises(RuntimeError, match="one-shot migration script"):
        Database(widget_registry(Version1.widget), path=path)


def test_unchanged_schema_skips_reconciliation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = str(tmp_path / "data.db")
    registry = widget_registry(Version1.widget)
    Database(registry, path=path)
    forbid_reconciliation(monkeypatch)
    reopened = Database(registry, path=path)
    assert Store(reopened).read_dict(Version1.widget.name) == {}


def test_fresh_database_skips_reconciliation(monkeypatch: pytest.MonkeyPatch) -> None:
    forbid_reconciliation(monkeypatch)
    Database(schema, path=":memory:")


def forbid_reconciliation(monkeypatch: pytest.MonkeyPatch) -> None:
    # reaching the deferred import then fails with an ImportError
    monkeypatch.delattr("package_utils.storage.migrations.reconcile_schema")


def test_foreign_tables_are_ignored(db: Database) -> None:
    with db.engine.begin() as connection:
        connection.execute(text("CREATE TABLE foreign_tool (id INTEGER PRIMARY KEY)"))
    assert schema_diff(db) == []


def test_no_drift_when_schema_matches(db: Database) -> None:
    assert schema_diff(db) == []


def test_diff_detects_a_missing_table() -> None:
    class Columns:
        class widget:  # noqa: N801
            id_ = Annotated[int, Key()]
            name = Annotated[str, Field()]

    registry = Schema()
    registry.scope(Columns.widget)
    database = Database(registry, path=":memory:")
    with database.engine.begin() as connection:
        connection.execute(text("DROP TABLE widget"))
    operations = schema_diff(database)
    assert operations
    assert any("widget" in str(operation) for operation in operations)


def test_diff_uses_the_registered_metadata() -> None:
    database = Database(schema, path=":memory:")
    assert set(database.tables.metadata.tables) == {
        scope.table for scope in schema.scopes
    }
