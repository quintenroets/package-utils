from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.pool import StaticPool

from .read_cache import ReadCache
from .tables import build_tables

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from sqlalchemy import Executable, RowMapping, Table
    from sqlalchemy.engine import Connection, Engine

    from .schema import Schema, Scope
    from .tables import SchemaTables

    ReadRows = Callable[[Any], Any]

UNSET_ENGINE: Engine = cast("Engine", None)


@dataclass
class Database:
    schema: Schema
    path: str = ":memory:"
    single_writer: bool = False
    engine: Engine = UNSET_ENGINE
    local: threading.local = field(default_factory=threading.local, init=False)
    tables: SchemaTables = field(init=False)
    cache: ReadCache | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if self.engine is UNSET_ENGINE:
            self.engine = create_engine_for(f"sqlite:///{self.path}")
        if self.engine.dialect.name == "sqlite":
            event.listen(self.engine, "connect", configure_sqlite_connection)
        self.tables = build_tables(self.schema)
        self.synchronize_schema()
        if self.single_writer:
            self.cache = ReadCache()

    def synchronize_schema(self) -> None:
        """Bring the live schema up to the registry, desired-state style.

        Missing tables are created and purely additive drift is applied in
        place; non-additive drift raises for a standalone one-shot script. The
        DDL fingerprint stored in SQLite's `user_version` makes the no-change
        startup a single PRAGMA read; other backends reconcile every startup.
        """
        fingerprint = self.tables.fingerprint(self.engine)
        if self.stored_fingerprint() != fingerprint:
            populated = bool(inspect(self.engine).get_table_names())
            self.tables.metadata.create_all(self.engine, checkfirst=populated)
            if populated:
                # deferred so alembic is only imported when drift is possible
                from .migrations import reconcile_schema  # noqa: PLC0415

                reconcile_schema(self)
            self.record_fingerprint(fingerprint)

    def stored_fingerprint(self) -> int | None:
        # only SQLite offers a version slot; other backends always answer unknown
        sqlite = self.dialect_name == "sqlite"
        statement = "PRAGMA user_version" if sqlite else "SELECT NULL"
        with self.engine.connect() as connection:
            return cast("int | None", connection.exec_driver_sql(statement).scalar())

    def record_fingerprint(self, fingerprint: int) -> None:
        if self.dialect_name == "sqlite":
            with self.engine.begin() as connection:
                connection.exec_driver_sql(f"PRAGMA user_version = {fingerprint}")

    @property
    def dialect_name(self) -> str:
        return self.engine.dialect.name

    def table_of(self, scope: Scope) -> Table:
        return self.tables.table_of(scope)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self.active_connection is not None:
            yield  # nested block composes into the active transaction
        else:
            with self.engine.connect() as connection:
                self.local.connection = connection
                transaction = connection.begin()
                try:
                    yield
                except BaseException:
                    transaction.rollback()  # cache holds only committed reads, intact
                    raise
                else:
                    transaction.commit()
                    self.record_write()  # commit publishes the writes to other reads
                finally:
                    self.local.connection = None

    @property
    def active_connection(self) -> Connection | None:
        return cast("Connection | None", getattr(self.local, "connection", None))

    def fetch_one(self, statement: Executable, params: Any = None) -> RowMapping | None:
        return cast("RowMapping | None", self.fetch(statement, params, fetch_first_row))

    def fetch_all(self, statement: Executable, params: Any = None) -> list[RowMapping]:
        return cast("list[RowMapping]", self.fetch(statement, params, fetch_row_list))

    def fetch(self, statement: Executable, params: Any, read_rows: ReadRows) -> Any:
        read = partial(self.uncached_fetch, statement, params, read_rows)
        if self.cache is None or self.active_connection is not None:
            # reads inside a transaction see uncommitted state, so they neither
            # serve from nor populate the cache shared with other connections
            result = read()
        else:
            result = self.cache.fetch(cache_key(statement, params), read)
        return result

    def uncached_fetch(
        self,
        statement: Executable,
        params: Any,
        read_rows: ReadRows,
    ) -> Any:
        with self.reading() as connection:
            return read_rows(connection.execute(statement, params))

    def run(self, statement: Executable, params: Any = None) -> None:
        with self.writing() as connection:
            connection.execute(statement, params)
        self.record_autocommit()

    def run_many(self, statement: Executable, params: list[Any]) -> None:
        with self.writing() as connection:
            connection.execute(statement, params)
        self.record_autocommit()

    def record_autocommit(self) -> None:
        if self.active_connection is None:  # inside a transaction, commit records it
            self.record_write()

    def record_write(self) -> None:
        if self.cache is not None:
            self.cache.record_write()

    @contextmanager
    def reading(self) -> Iterator[Connection]:
        connection = self.active_connection
        if connection is not None:
            yield connection
        else:
            with self.engine.connect() as connection:
                yield connection

    @contextmanager
    def writing(self) -> Iterator[Connection]:
        connection = self.active_connection
        if connection is not None:
            yield connection
        else:
            with self.engine.begin() as connection:
                yield connection


def fetch_first_row(result: Any) -> Any:
    return result.mappings().fetchone()


def fetch_row_list(result: Any) -> list[Any]:
    return list(result.mappings())


def cache_key(statement: Any, params: Any) -> Any:
    """Key a read by its statement structure plus the bound values.

    `_generate_cache_key` gives the structural key (which encodes the projection
    — its SELECT column list — so different dataclasses reading the same row land
    on different keys) with the bound values abstracted out into `bindparams`.
    Combining the two keys a read without compiling the statement to a SQL string
    on every cache hit; `params` carries the raw `text()` escape hatch's values.
    """
    cache = statement._generate_cache_key()  # noqa: SLF001
    values = tuple(parameter.value for parameter in cache.bindparams)
    return (cache.key, values, frozenset((params or {}).items()))


def create_engine_for(url: str) -> Engine:
    options: dict[str, Any] = {}
    if url.startswith("sqlite"):
        # connections are handed across threads (pool, server workers)
        options["connect_args"] = {"check_same_thread": False}
        if ":memory:" in url or url == "sqlite://":
            # one shared connection so the in-memory schema survives every checkout
            options["poolclass"] = StaticPool
    return create_engine(url, **options)


def configure_sqlite_connection(dbapi_connection: Any, _: Any) -> None:
    cursor = dbapi_connection.cursor()
    for pragma in ("foreign_keys=ON", "busy_timeout=5000", "journal_mode=WAL"):
        cursor.execute(f"PRAGMA {pragma}")
    cursor.close()
