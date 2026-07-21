from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Annotated

import pytest
from hypothesis import given, settings, strategies
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from package_utils.storage import (
    Database,
    Field,
    Store,
    instances_from,
)
from package_utils.storage.read_cache import CACHE_CAPACITY
from package_utils.storage.schema import attr_field_type_map, child_specs

from .fields import (
    Album,
    Blob,
    Block,
    Bucket,
    Catalog,
    Color,
    Coordinates,
    Detail,
    Entry,
    Event,
    Fields,
    Item,
    Log,
    Marker,
    Meta,
    Node,
    Part,
    Phase,
    Score,
    Setting,
    Target,
    Tick,
    Track,
    schema,
)

if TYPE_CHECKING:
    from pathlib import Path

    from hypothesis.strategies import SearchStrategy


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


def test_dataclass_round_trip(db: Database) -> None:
    node = rich_node()
    Store(db).write(node)
    assert Store(db)["show"].read(Node) == node


def test_read_missing_dataclass_returns_none(db: Database) -> None:
    assert Store(db)["absent"].read(Node) is None


def test_single_field_round_trip(db: Database) -> None:
    Store(db)["solo"].write(Fields.node.label, "value")
    assert Store(db)["solo"].read(Fields.node.label) == "value"


def test_single_field_read_missing_returns_none(db: Database) -> None:
    assert Store(db)["absent"].read(Fields.node.label) is None


def test_bool_field_deserializes(db: Database) -> None:
    Store(db)["flagged"].write(Fields.node.active, value=True)
    assert Store(db)["flagged"].read(Fields.node.active) is True


def test_read_or_default_missing(db: Database) -> None:
    assert Store(db).read_or_default(Setting) == Setting()


def test_read_or_default_present(db: Database) -> None:
    Store(db).write(Setting(value="set"))
    assert Store(db).read_or_default(Setting) == Setting(value="set")


def test_singleton_round_trip(db: Database) -> None:
    Store(db).write(Setting(value="only"))
    assert Store(db).read(Setting) == Setting(value="only")


def test_read_list_at_root(db: Database) -> None:
    Store(db).write(Node(key="a"))
    Store(db).write(Node(key="b"))
    keys = [node.key for node in Store(db).read_list(Node)]
    assert keys == ["a", "b"]


def test_read_dict_single_key_unwraps(db: Database) -> None:
    Store(db).write(rich_node())
    items = Store(db)["show"].read_dict(Item)
    assert set(items) == {0, 1}


def test_read_dict_multi_key(db: Database) -> None:
    Store(db).write(rich_node())
    parts = Store(db)["show"].read_dict(Part)
    assert parts == {(0, 0): Part(title="a"), (0, 1): Part(title="b")}


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


def test_nested_transaction_commits_once(db: Database) -> None:
    store = Store(db)
    node = rich_node()
    with store.transaction():
        store.write(node)
    assert store["show"].read(Node) == node


def test_single_row_read_requires_full_key(db: Database) -> None:
    with pytest.raises(ValueError, match="full key"):
        Store(db)["partial"].read(Part)


def test_instances_from_maps_raw_text_rows(db: Database) -> None:
    node = Node(key="raw", label="cover", active=True, created=date(2026, 6, 13))
    Store(db).write(node)
    rows = db.fetch_all(text("SELECT * FROM node WHERE key = :key"), {"key": "raw"})
    assert instances_from(Node, rows) == [node]


def test_instances_from_coerces_raw_datetime(db: Database) -> None:
    at = datetime(2026, 6, 13, 9, 30, tzinfo=timezone.utc)
    Store(db).write(Event(at=at, note="started"))
    rows = db.fetch_all(text("SELECT * FROM event"))
    assert instances_from(Event, rows) == [Event(at=at, note="started")]


def test_read_inside_transaction_sees_pending_write(db: Database) -> None:
    store = Store(db)
    with db.transaction():
        store.write(Node(key="pending", label="L"))
        pending = store["pending"].read(Node)
    assert pending is not None
    assert pending.label == "L"


def test_datetime_key_round_trip(db: Database) -> None:
    at = datetime(2026, 6, 13, 9, 30, 15, tzinfo=timezone.utc)
    event = Event(at=at, note="started", ticks=[Tick(value=1), Tick(value=2)])
    Store(db).write(event)
    assert Store(db)[at].read(Event) == event
    assert Store(db).read_dict(Event) == {at: event}


def rich_catalog() -> Catalog:
    return Catalog(
        key="main",
        name="Main",
        scores={"a": Score(points=1), "b": Score(points=2)},
        tags=["x", "y", "z"],
        ratings={"critics": 0.8, "users": 0.6},
        buckets={
            "first": Bucket(title="First", measures={"plays": 10, "skips": 2}),
            "second": Bucket(title="Second"),
        },
        albums={
            "debut": Album(tracks={"one": Track(length=180), "two": Track(length=200)}),
        },
    )


def test_collection_round_trip(db: Database) -> None:
    catalog = rich_catalog()
    Store(db).write(catalog)
    assert Store(db)["main"].read(Catalog) == catalog


def read_catalog(db: Database, key: str = "main") -> Catalog:
    catalog = Store(db)[key].read(Catalog)
    assert catalog is not None
    return catalog


def test_keyed_record_child_reads_as_dict(db: Database) -> None:
    Store(db).write(rich_catalog())
    assert read_catalog(db).scores == {"a": Score(points=1), "b": Score(points=2)}


def test_scalar_list_child_preserves_order(db: Database) -> None:
    Store(db).write(rich_catalog())
    assert read_catalog(db).tags == ["x", "y", "z"]


def test_scalar_dict_child_round_trips(db: Database) -> None:
    Store(db).write(rich_catalog())
    assert read_catalog(db).ratings == {"critics": 0.8, "users": 0.6}


def test_nested_collection_round_trips(db: Database) -> None:
    Store(db).write(rich_catalog())
    assert read_catalog(db).buckets["first"].measures == {"plays": 10, "skips": 2}


def test_collection_overwrite_replaces_children(db: Database) -> None:
    Store(db).write(rich_catalog())
    Store(db).write(Catalog(key="main", name="Main", tags=["only"]))
    catalog = read_catalog(db)
    assert catalog.tags == ["only"]
    assert catalog.scores == {}
    assert catalog.buckets == {}


def test_collection_delete_cascades(db: Database) -> None:
    Store(db).write(rich_catalog())
    Store(db)["main"].delete(Catalog)
    assert Store(db)["main"].read(Catalog) is None
    assert Store(db)["main"]["first"].read_dict(Bucket) == {}


def test_collections_across_roots_read_per_level(db: Database) -> None:
    Store(db).write(rich_catalog())
    Store(db).write(Catalog(key="other", name="Other", tags=["q"]))
    catalogs = {catalog.key: catalog for catalog in Store(db).read_list(Catalog)}
    assert catalogs["main"].tags == ["x", "y", "z"]
    assert catalogs["other"].tags == ["q"]


def test_pure_container_record_round_trips(db: Database) -> None:
    Store(db).write(rich_catalog())
    album = read_catalog(db).albums["debut"]
    assert album == Album(tracks={"one": Track(length=180), "two": Track(length=200)})


def test_standalone_pure_container_write_and_rewrite(db: Database) -> None:
    Store(db).write(Catalog(key="main", name="Main"))
    Store(db)["main"]["debut"].write(Album(tracks={"one": Track(length=180)}))
    assert read_catalog(db).albums == {
        "debut": Album(tracks={"one": Track(length=180)}),
    }
    Store(db)["main"]["debut"].write(Album(tracks={"two": Track(length=200)}))
    assert read_catalog(db).albums["debut"].tracks == {"two": Track(length=200)}


def test_standalone_scalar_dict_round_trips(db: Database) -> None:
    downloads = {"id1": "Song A", "id2": "Song B"}
    Store(db).write_dict(Fields.download.name, downloads)
    assert Store(db).read_dict(Fields.download.name) == downloads


def test_standalone_scalar_dict_entry_access(db: Database) -> None:
    Store(db).write_dict(Fields.download.name, {"id1": "Song A"})
    Store(db)["id2"].write(Fields.download.name, "Song B")
    assert Store(db)["id1"].read(Fields.download.name) == "Song A"
    both = {"id1": "Song A", "id2": "Song B"}
    assert Store(db).read_dict(Fields.download.name) == both


def test_standalone_scalar_dict_replaces_on_rewrite(db: Database) -> None:
    Store(db).write_dict(Fields.download.name, {"id1": "Song A", "id2": "Song B"})
    Store(db).write_dict(Fields.download.name, {"id3": "Song C"})
    assert Store(db).read_dict(Fields.download.name) == {"id3": "Song C"}


def test_standalone_scalar_list_round_trips(db: Database) -> None:
    Store(db).write_list(Fields.queued.url, ["a", "b", "c"])
    assert Store(db).read_list(Fields.queued.url) == ["a", "b", "c"]


def test_bytes_column_round_trips(db: Database) -> None:
    payload = bytes(range(256)) * 4
    Store(db).write(Blob(key="raw", payload=payload))
    stored = Store(db)["raw"].read(Blob)
    assert stored is not None
    assert stored.payload == payload


def test_enum_column_round_trips(db: Database) -> None:
    catalog = Catalog(key="main", color=Color.blue)
    Store(db).write(catalog)
    assert read_catalog(db).color == Color.blue


def test_instances_from_coerces_raw_enum(db: Database) -> None:
    Store(db).write(Catalog(key="main", color=Color.blue))
    rows = db.fetch_all(text("SELECT * FROM catalog"))
    assert instances_from(Catalog, rows)[0].color == Color.blue


def test_unannotated_collection_is_not_a_child() -> None:
    @dataclass
    class Loose:
        values: list[str] = field(default_factory=list)

    assert child_specs(Loose) == ()


def test_composite_key_round_trip(db: Database) -> None:
    target = Target(plan="P", week=2, session="HL", volume=5)
    Store(db).write(target)
    assert Store(db)["P"][2]["HL"].read(Target) == target


def test_composite_key_read_dict_returns_tuple_keys(db: Database) -> None:
    Store(db).write(Target(plan="P", week=1, session="HL", volume=4))
    Store(db).write(Target(plan="P", week=1, session="S3", volume=6))
    targets = Store(db).read_dict(Target)
    assert set(targets) == {("P", 1, "HL"), ("P", 1, "S3")}


def test_composite_key_parent_child_round_trip(db: Database) -> None:
    phase = Phase(plan="P", week=1, note="intro", blocks=[Block(label="a"), Block()])
    Store(db).write(phase)
    assert Store(db)["P"][1].read(Phase) == phase


def test_composite_key_child_cascades_on_delete(db: Database) -> None:
    Store(db).write(Phase(plan="P", week=1, blocks=[Block(label="a")]))
    Store(db)["P"][1].delete(Phase)
    assert Store(db)["P"][1].read_list(Block) == []


def test_satellite_round_trip_and_cascade(db: Database) -> None:
    at = datetime(2026, 6, 18, 9, 30, tzinfo=timezone.utc)
    Store(db).write(Log(at=at, label="run"))
    Store(db)[at].write(Detail(amount=42, note="ok"))
    assert Store(db)[at].read(Detail) == Detail(amount=42, note="ok")
    Store(db)[at].write(Detail(amount=7, note=None))
    assert Store(db)[at].read(Detail) == Detail(amount=7, note=None)
    Store(db)[at].delete(Log)
    assert Store(db)[at].read(Detail) is None


def index_names(db: Database) -> set[str]:
    rows = db.fetch_all(text("SELECT name FROM sqlite_master WHERE type = 'index'"))
    return {row["name"] for row in rows}


def test_plain_index_is_created(db: Database) -> None:
    assert "ix_entry_source_low" in index_names(db)


def test_partial_index_records_its_predicate(db: Database) -> None:
    row = db.fetch_one(
        text("SELECT sql FROM sqlite_master WHERE name = :name"),
        {"name": "ix_entry_source_id"},
    )
    assert row is not None
    assert "source = 'polar'" in row["sql"]


def test_partial_unique_index_rejects_matching_duplicate(db: Database) -> None:
    Store(db).write(Entry(id="1", source="polar", source_id="X"))
    with pytest.raises(IntegrityError):
        Store(db).write(Entry(id="2", source="polar", source_id="X"))


def test_partial_unique_index_ignores_non_matching_rows(db: Database) -> None:
    Store(db).write(Entry(id="3", source="hevy", source_id="Y"))
    Store(db).write(Entry(id="4", source="hevy", source_id="Y"))
    assert len(Store(db).read_list(Entry)) == 2


def test_check_constraint_rejects_violation(db: Database) -> None:
    with pytest.raises(IntegrityError):
        Store(db).write(Entry(id="bad", low=5, high=1))


def test_check_constraint_allows_valid_row(db: Database) -> None:
    entry = Entry(id="ok", low=1, high=5)
    Store(db).write(entry)
    assert Store(db)["ok"].read(Entry) == entry


def test_column_returns_field_name() -> None:
    assert schema.column(Fields.entry.source_id) == "source_id"


def test_table_of_returns_scope_table() -> None:
    assert schema.table_of(Entry) == "entry"


def test_attr_field_type_map_skips_non_annotated() -> None:
    @dataclass
    class Mixed:
        x: int = 0
        y: Annotated[int, Field(int)] = 0

    result = attr_field_type_map(Mixed)
    assert "x" not in result
    assert "y" in result


def test_attr_field_type_map_skips_annotated_without_field() -> None:
    @dataclass
    class Tagged:
        x: Annotated[int, "not_a_field"] = 0
        y: Fields.node.label = ""

    result = attr_field_type_map(Tagged)
    assert "x" not in result
    assert "y" in result


def test_run_many_persists_across_connections(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    first = Database(schema, path=db_path)
    Store(first)["persisted"].write(Fields.node.label, "")
    Store(first)["persisted"].insert_list([Item(title="x")])
    second = Database(schema, path=db_path)
    assert Store(second)["persisted"].read_list(Item) == [Item(title="x")]


def node_strategy() -> SearchStrategy[Node]:
    text = strategies.text()
    count = strategies.integers(min_value=0, max_value=3)
    parts = strategies.builds(Part, title=text)
    items = strategies.builds(
        Item,
        title=text,
        parts=strategies.lists(parts, max_size=3),
    )
    return strategies.builds(
        Node,
        key=strategies.text(min_size=1),
        label=text,
        ratio=strategies.none()
        | strategies.floats(allow_nan=False, allow_infinity=False),
        active=strategies.booleans(),
        meta=strategies.builds(Meta, tag=text, count=count),
        items=strategies.lists(items, max_size=3),
    )


@settings(max_examples=25)
@given(node=node_strategy())
def test_random_tree_round_trip(node: Node) -> None:
    database = Database(schema, path=":memory:")
    Store(database).write(node)
    assert Store(database)[node.key].read(Node) == node


def test_consumer_column_type_round_trips(db: Database) -> None:
    marker = Marker(key="m", point=Coordinates(7, 9))
    Store(db).write(marker)
    assert Store(db)["m"].read(Marker) == marker


def test_single_writer_caches_decoded_value() -> None:
    db = Database(schema, single_writer=True)
    Store(db)["m"].write(Marker(key="m", point=Coordinates(1, 2)))
    first = Store(db)["m"].read(Fields.marker.point)
    second = Store(db)["m"].read(Fields.marker.point)
    assert first is second
    assert first == Coordinates(1, 2)


def test_default_database_redecodes_each_read() -> None:
    db = Database(schema)
    Store(db)["m"].write(Marker(key="m", point=Coordinates(1, 2)))
    first = Store(db)["m"].read(Fields.marker.point)
    second = Store(db)["m"].read(Fields.marker.point)
    assert first == second
    assert first is not second


def test_write_busts_read_cache() -> None:
    db = Database(schema, single_writer=True)
    store = Store(db)["m"]
    store.write(Marker(key="m", point=Coordinates(1, 2)))
    assert store.read(Fields.marker.point) == Coordinates(1, 2)
    store.write(Marker(key="m", point=Coordinates(3, 4)))
    assert store.read(Fields.marker.point) == Coordinates(3, 4)


def test_rollback_busts_read_cache() -> None:
    db = Database(schema, single_writer=True)
    store = Store(db)["m"]
    store.write(Marker(key="m", point=Coordinates(1, 2)))
    assert store.read(Fields.marker.point) == Coordinates(1, 2)
    with pytest.raises(RuntimeError), db.transaction():  # noqa: PT012
        store.write(Fields.marker.point, Coordinates(9, 9))
        assert store.read(Fields.marker.point) == Coordinates(9, 9)
        raise RuntimeError
    assert store.read(Fields.marker.point) == Coordinates(1, 2)


def test_concurrent_reader_sees_neither_uncommitted_nor_stale(tmp_path: Path) -> None:
    # a file DB hands each thread its own connection (an in-memory StaticPool would
    # share one), so the reader's isolation from the open write transaction is real
    db = Database(schema, path=str(tmp_path / "concurrent.db"), single_writer=True)
    store = Store(db)["m"]
    store.write(Marker(key="m", point=Coordinates(1, 2)))

    writing = threading.Event()
    read_committed = threading.Event()
    committed = threading.Event()

    def writer() -> None:
        with db.transaction():
            store.write(Fields.marker.point, Coordinates(9, 9))
            store.read(Fields.marker.point)  # in-txn read must not leak into the cache
            writing.set()
            read_committed.wait(timeout=5)
        committed.set()

    thread = threading.Thread(target=writer)
    thread.start()
    writing.wait(timeout=5)
    assert store.read(Fields.marker.point) == Coordinates(1, 2)  # not the dirty write
    read_committed.set()
    committed.wait(timeout=5)
    thread.join()
    assert store.read(Fields.marker.point) == Coordinates(9, 9)  # not the stale value


def test_read_cache_evicts_beyond_capacity() -> None:
    db = Database(schema, single_writer=True)
    count = CACHE_CAPACITY + 5
    with db.transaction():
        for index in range(count):
            key = str(index)
            Store(db)[key].write(Marker(key=key, point=Coordinates(index, index)))
    for index in range(count):
        Store(db)[str(index)].read(Fields.marker.point)
    assert db.cache is not None
    assert len(db.cache.entries) == CACHE_CAPACITY
