from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Annotated, NamedTuple

from sqlalchemy import LargeBinary, TypeDecorator

from package_utils.storage import Field, Key, Schema

if TYPE_CHECKING:
    from sqlalchemy.engine import Dialect

MIN_DATETIME = datetime.min.replace(tzinfo=timezone.utc)


class Color(Enum):
    red = "red"
    blue = "blue"


class Coordinates(NamedTuple):
    """Stand-in for keybias's numpy payload: a consumer type with a custom codec.

    Not a dataclass and not a typing collection, so the registry treats it as one
    flat column rather than a nested record or child scope; the codec below owns
    its (de)serialization the way keybias's `NumpyArray` owns `np.load`/`np.save`.
    """

    x: int
    y: int


class CoordinatesBlob(TypeDecorator[Coordinates]):
    """A reversible bytes codec a consumer registers, like keybias's NumpyArray.

    `process_result_value` builds a fresh `Coordinates` each call, so a cache hit
    is observable as object identity — proving the cache sits above this decode.
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(
        self,
        value: Coordinates | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> bytes | None:
        return None if value is None else json.dumps([value.x, value.y]).encode()

    def process_result_value(
        self,
        value: bytes | None,
        dialect: Dialect,  # noqa: ARG002
    ) -> Coordinates | None:
        return None if value is None else Coordinates(*json.loads(value))


class Fields:
    class node:
        key = Annotated[str, Key()]
        label = Annotated[str, Field()]
        ratio = Annotated[float | None, Field()]
        active = Annotated[bool, Field()]
        created = Annotated[date | None, Field()]

        class meta:
            tag = Annotated[str, Field()]
            count = Annotated[int, Field()]

    class item:
        idx = Annotated[int, Key()]
        title = Annotated[str, Field()]

    class part:
        idx = Annotated[int, Key()]
        title = Annotated[str, Field()]

    class setting:
        value = Annotated[str, Field()]

    class event:
        at = Annotated[datetime, Key()]
        note = Annotated[str, Field()]

    class tick:
        idx = Annotated[int, Key()]
        value = Annotated[int, Field()]

    class catalog:
        key = Annotated[str, Key()]
        name = Annotated[str, Field()]
        color = Annotated[Color, Field()]

    class score:
        grade = Annotated[str, Key()]
        points = Annotated[int, Field()]

    class tag:
        idx = Annotated[int, Key()]
        text = Annotated[str, Field()]

    class rating:
        source = Annotated[str, Key()]
        value = Annotated[float, Field()]

    class bucket:
        name = Annotated[str, Key()]
        title = Annotated[str, Field()]

    class measure:
        metric = Annotated[str, Key()]
        amount = Annotated[int, Field()]

    class album:
        title = Annotated[str, Key()]

    class track:
        name = Annotated[str, Key()]
        length = Annotated[int, Field()]

    class download:
        id = Annotated[str, Key()]
        name = Annotated[str, Field()]

    class queued:
        idx = Annotated[int, Key()]
        url = Annotated[str, Field()]

    class blob:
        key = Annotated[str, Key()]
        payload = Annotated[bytes, Field()]

    class marker:
        key = Annotated[str, Key()]
        point = Annotated[Coordinates, Field()]

    class target:
        plan = Annotated[str, Key()]
        week = Annotated[int, Key()]
        session = Annotated[str, Key()]
        volume = Annotated[int, Field()]

    class phase:
        plan = Annotated[str, Key()]
        week = Annotated[int, Key()]
        note = Annotated[str, Field()]

    class block:
        idx = Annotated[int, Key()]
        label = Annotated[str, Field()]

    class entry:
        id = Annotated[str, Key()]
        source = Annotated[str, Field()]
        source_id = Annotated[str, Field()]
        low = Annotated[int, Field()]
        high = Annotated[int, Field()]

    class log:
        at = Annotated[datetime, Key()]
        label = Annotated[str, Field()]

    class detail:
        amount = Annotated[int, Field()]
        note = Annotated[str | None, Field()]


@dataclass
class Meta:
    tag: Fields.node.meta.tag = ""
    count: Fields.node.meta.count = 0


@dataclass
class Part:
    title: Fields.part.title = ""


@dataclass
class Item:
    title: Fields.item.title = ""
    parts: list[Part] = field(default_factory=list)


@dataclass
class Node:
    key: Fields.node.key = ""
    label: Fields.node.label = ""
    ratio: Fields.node.ratio = None
    active: Fields.node.active = False
    created: Fields.node.created = None
    meta: Meta = field(default_factory=Meta)
    items: list[Item] = field(default_factory=list)


@dataclass
class Setting:
    value: Fields.setting.value = ""


@dataclass
class Tick:
    value: Fields.tick.value = 0


@dataclass
class Event:
    at: Fields.event.at = MIN_DATETIME
    note: Fields.event.note = ""
    ticks: list[Tick] = field(default_factory=list)


@dataclass
class Score:
    points: Fields.score.points = 0


@dataclass
class Bucket:
    title: Fields.bucket.title = ""
    measures: Annotated[dict[str, int], Fields.measure.amount] = field(
        default_factory=dict,
    )


@dataclass
class Track:
    length: Fields.track.length = 0


@dataclass
class Album:
    tracks: dict[str, Track] = field(default_factory=dict)


@dataclass
class Blob:
    key: Fields.blob.key = ""
    payload: Fields.blob.payload = b""


@dataclass
class Marker:
    key: Fields.marker.key = ""
    point: Fields.marker.point = field(default_factory=lambda: Coordinates(0, 0))


@dataclass
class Target:
    plan: Fields.target.plan = ""
    week: Fields.target.week = 0
    session: Fields.target.session = ""
    volume: Fields.target.volume = 0


@dataclass
class Block:
    label: Fields.block.label = ""


@dataclass
class Phase:
    plan: Fields.phase.plan = ""
    week: Fields.phase.week = 0
    note: Fields.phase.note = ""
    blocks: list[Block] = field(default_factory=list)


@dataclass
class Entry:
    id: Fields.entry.id = ""
    source: Fields.entry.source = ""
    source_id: Fields.entry.source_id = ""
    low: Fields.entry.low = 0
    high: Fields.entry.high = 0


@dataclass
class Log:
    at: Fields.log.at = MIN_DATETIME
    label: Fields.log.label = ""


@dataclass
class Detail:
    amount: Fields.detail.amount = 0
    note: Fields.detail.note = None


@dataclass
class Catalog:
    key: Fields.catalog.key = ""
    name: Fields.catalog.name = ""
    color: Fields.catalog.color = Color.red
    scores: dict[str, Score] = field(default_factory=dict)
    tags: Annotated[list[str], Fields.tag.text] = field(default_factory=list)
    ratings: Annotated[dict[str, float], Fields.rating.value] = field(
        default_factory=dict,
    )
    buckets: dict[str, Bucket] = field(default_factory=dict)
    albums: dict[str, Album] = field(default_factory=dict)


schema = Schema()
node = schema.scope(Fields.node)
item = schema.scope(Fields.item, parent=node)
part = schema.scope(Fields.part, parent=item)
setting = schema.scope(Fields.setting)
event = schema.scope(Fields.event)
tick = schema.scope(Fields.tick, parent=event)
catalog = schema.scope(Fields.catalog)
score = schema.scope(Fields.score, parent=catalog)
tag = schema.scope(Fields.tag, parent=catalog)
rating = schema.scope(Fields.rating, parent=catalog)
bucket = schema.scope(Fields.bucket, parent=catalog)
measure = schema.scope(Fields.measure, parent=bucket)
album = schema.scope(Fields.album, parent=catalog)
track = schema.scope(Fields.track, parent=album)
download = schema.scope(Fields.download)
queued = schema.scope(Fields.queued)
blob = schema.scope(Fields.blob)
schema.register_column_type(Coordinates, CoordinatesBlob())
marker = schema.scope(Fields.marker)
target = schema.scope(Fields.target)
phase = schema.scope(Fields.phase)
block = schema.scope(Fields.block, parent=phase)
entry = schema.scope(Fields.entry)
schema.index(Fields.entry.source, Fields.entry.low)
schema.index(Fields.entry.source_id, where="source = 'polar'", unique=True)
schema.check(entry, "high >= low")
log = schema.scope(Fields.log)
detail = schema.scope(Fields.detail, parent=log)  # 1:1 satellite: no own key
