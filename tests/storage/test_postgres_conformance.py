"""Runs the storage round-trip against a real PostgreSQL backend.

Postgres is a supported production backend; this suite exercises the same
behaviours the SQLite suite does against a genuinely different engine. It is
skipped unless ``STORAGE_TEST_POSTGRES_DSN`` (a SQLAlchemy URL such as
``postgresql+psycopg://user:pw@host/db``) points at a reachable server, and is
omitted from coverage because it depends on external infrastructure.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from package_utils.storage import Database, Store, build_tables, instances_from

from .fields import (
    Album,
    Bucket,
    Catalog,
    Color,
    Event,
    Fields,
    Item,
    Meta,
    Node,
    Part,
    Score,
    Track,
    schema,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

pytest.importorskip("psycopg")

DSN = os.environ.get("STORAGE_TEST_POSTGRES_DSN")


def rich_node() -> Node:
    return Node(
        key="show",
        label="Show",
        ratio=0.5,
        active=True,
        created=date(2026, 6, 13),
        meta=Meta(tag="featured", count=3),
        items=[
            Item(title="first", parts=[Part(title="a"), Part(title="b")]),
            Item(title="second"),
        ],
    )


@pytest.fixture
def db() -> Iterator[Database]:
    if DSN is None:
        pytest.skip("STORAGE_TEST_POSTGRES_DSN is not set")
    engine = create_engine(DSN)
    try:
        engine.connect().close()
    except OperationalError as error:
        pytest.skip(f"PostgreSQL server unreachable: {error}")
    # leftovers from a crashed run must go before construction reconciles
    build_tables(schema).metadata.drop_all(engine)
    database = Database(schema, engine=engine)
    yield database
    database.tables.metadata.drop_all(engine)
    engine.dispose()


def test_dataclass_round_trip(db: Database) -> None:
    node = rich_node()
    Store(db).write(node)
    assert Store(db)["show"].read(Node) == node


def test_single_field_round_trip(db: Database) -> None:
    Store(db)["solo"].write(Fields.node.label, "value")
    assert Store(db)["solo"].read(Fields.node.label) == "value"


def test_read_list_orders_by_key(db: Database) -> None:
    Store(db).write(Node(key="a"))
    Store(db).write(Node(key="b"))
    assert [node.key for node in Store(db).read_list(Node)] == ["a", "b"]


def test_delete_cascades(db: Database) -> None:
    Store(db).write(rich_node())
    Store(db)["show"].delete(Node)
    assert Store(db)["show"].read(Node) is None
    assert Store(db)["show"].read_list(Item) == []


def test_transaction_rollback(db: Database) -> None:
    store = Store(db)["rollback"]
    store.write(Fields.node.label, "")
    with pytest.raises(RuntimeError), db.transaction():  # noqa: PT012
        store.insert_list([Item(title="x")])
        raise RuntimeError
    assert store.read_list(Item) == []


def test_datetime_key_round_trip(db: Database) -> None:
    at = datetime(2026, 6, 13, 9, 30, 15, tzinfo=timezone.utc)
    event = Event(at=at, note="started")
    Store(db).write(event)
    assert Store(db)[at].read(Event) == event


def test_instances_from_raw_rows(db: Database) -> None:
    Store(db).write(Node(key="raw", label="cover"))
    rows = db.fetch_all(text("SELECT * FROM node WHERE key = :key"), {"key": "raw"})
    assert instances_from(Node, rows) == [Node(key="raw", label="cover")]


def test_collection_round_trip(db: Database) -> None:
    catalog = Catalog(
        key="main",
        name="Main",
        color=Color.blue,
        scores={"a": Score(points=1)},
        tags=["x", "y"],
        ratings={"critics": 0.8},
        buckets={"first": Bucket(title="First", measures={"plays": 10})},
        albums={"debut": Album(tracks={"one": Track(length=180)})},
    )
    Store(db).write(catalog)
    assert Store(db)["main"].read(Catalog) == catalog


def test_standalone_scalar_dict_round_trip(db: Database) -> None:
    downloads = {"id1": "Song A", "id2": "Song B"}
    Store(db).write_dict(Fields.download.name, downloads)
    assert Store(db).read_dict(Fields.download.name) == downloads


def test_standalone_scalar_list_round_trip(db: Database) -> None:
    Store(db).write_list(Fields.queued.url, ["a", "b", "c"])
    assert Store(db).read_list(Fields.queued.url) == ["a", "b", "c"]
