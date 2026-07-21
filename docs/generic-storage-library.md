# Generic Storage Library

`package_utils.storage` is a reusable persistence layer that collapses hand-rolled, structured-record storage — scattered file I/O, manual tree assembly, ad-hoc schemas — into typed dataclass projections over **SQLAlchemy Core**. It runs on **SQLite** (default) and **PostgreSQL**, both production backends.

A consumer declares its columns once as a `Fields` tree, registers scopes on a `Schema`, and reads/writes domain dataclasses through a key-prefix `Store`. The library owns the registry, the row↔dataclass mapping, recursive tree read/write, transactions, and FK-cascade DDL; the consumer owns only its domain layer.

> The history behind these decisions — the bespoke-then-Core migration, the superseded Dialect/Backend layer, rejected alternatives, and per-consumer migration learnings — lives in [storage-decision-log.md](storage-decision-log.md). This document describes the **current** design only.

Source: `src/package_utils/storage/` — `schema.py` (registry), `tables.py` (Core `MetaData`), `store.py` (access layer), `database.py` (engine + transactions), `mapping.py` (row→dataclass), `read_cache.py`, `store_field.py`. Consumers: serie, music, powerplan, keybias.

## When this library is (and isn't) a fit

It earns its keep when a project has **all three** of:

- **structured records** — fixed-shape rows, not opaque blobs;
- **read-back / query** — the data is loaded again and reasoned over (filtered, aggregated, compared), not just written and forgotten;
- **persistence complexity worth collapsing** — scattered file I/O, hand-assembled trees, or an ad-hoc schema the typed `Fields` tree + projection dataclasses would unify.

**Not a fit** (do not migrate for consistency's sake):
- **Large binary caches** — torch/numpy tensors, model weights, datasets. Keep as files; cramming multi-MB blobs into SQLite is pure downside with no query benefit. (keybias stores only *small* arrays as app-layer BLOBs.)
- **Write-once-never-read artifacts** — per-run dumps a human reads and nothing loads back. Use YAML/JSON.
- **Input/config files** — hand-edited YAML read once at startup.

## The registry (`schema.py`)

A consumer declares its schema as a single nested **`Fields`** tree — one inner class per scope, each column an `Annotated[python_type, Field()]` or `Annotated[python_type, Key()]`:

```python
class Fields:
    class serie:
        name: Annotated[str, Key()]
        class download:
            enabled: Annotated[bool, Field()]
    class season:
        idx: Annotated[int, Key()]
```

- **`Field(eq=False)`** carries `type_` and `name`, both assigned post-construction by `assign_names` from the attribute path (`download.enabled` → column `download_enabled`, `DELIMITER = "_"`). `eq=False` is load-bearing: two columns named `image` in different scopes must stay identity-distinct so each maps to its own scope. The field carries **no scope** — scope is recovered from the field via `field_scopes`.
- **`Key(Field)`** marks a scope's own key column. A namespace may declare **multiple** `Key()`s (flat composite business keys); they are kept in declaration order as the PK and the FK key-prefix for child scopes.
- **`Scope`** (frozen) holds `table`, `key_columns`, `fields`, `parent`. `singleton` is derived: no key columns and no parent. The whole `Scope` machinery is internal — consumers navigate via dataclasses and `Fields.*` aliases.
- **`Schema.scope(namespace, parent=None)`** runs `assign_names`, splits `Key`s from regular fields, and builds `key_columns` as the parent's inherited keys plus this scope's own keys. `inherited_keys` renames a parent's own keys to `{parent.table}_{name}` (season → `(serie_name, idx)`, episode → `(serie_name, season_idx, idx)`) and copies ancestor fields to fresh identities per scope. A parented scope is always keyed (`keyed = bool(keys) or parent is not None`) — a keyless-parented scope is a **1:1 satellite** whose key *is* the inherited parent key.
- **`field_scopes`** inverts `key_columns + fields` → scope. `scope_of_field` / `scope_of_dataclass` (= scope of the dataclass's first annotated field; falls back to the parent of its first child scope for a pure-container record) recover scope without storing it on the field.
- **`attr_field_type_map(cls)`** walks `get_type_hints`, recursing into nested dataclass attributes to produce dotted paths (`download.enabled`), returning `{attr_path: (Field, base_type)}`. `base_type_of` strips `Optional` and reduces a parameterized generic to its origin (`NDArray[Any]` → `np.ndarray`) for codec lookup.

A domain dataclass uses the tree aliases directly as annotations (`name: Fields.serie.name = ""`); every storage field must have a default (NULL→default is load-bearing).

## The collection mapper (`ChildSpec`)

A collection-valued attribute maps to a child scope. `child_specs(cls)` returns the `ChildSpec`s for a dataclass; each is one of four shapes:

- `list[Record]` — positional `idx` key, dataclass element;
- `dict[Key, Record]` — explicit dict key, dataclass element;
- `Annotated[list[scalar], Fields.x.col]` — positional `idx` key, scalar in one value column;
- `Annotated[dict[Key, scalar], Fields.x.col]` — explicit dict key, scalar value column.

`ChildSpec` is an abstract base carrying `attr` + `keyed` (dict vs list → own key is the mapping key vs the enumerate index). The element kind is a real subtype — **`RecordSpec(cls)`** or **`ScalarSpec(value_field)`** — so "exactly one of cls/value_field" is structural, not a runtime tag. The store path is polymorphic over the spec (`scope_of`, `grandchildren`, `column_names`, `value_columns`, `collection_items`); the one mapping-layer conversion is `element_from(spec, row)` (`instance_from` vs scalar `coerce`). Nesting (`dict[str, dict[str, scalar]]`) falls out of the recursion: one SELECT per level, no N+1.

Scalar collections point their `Annotated` metadata at the value column's existing `Fields.*` alias — no new declaration syntax. No JSON column type: structured data always flattens to typed scopes, even when read/written only wholesale (schema uniformity, drift detection, queryability). App-layer serialization is reserved for **opaque binary** (numpy), never structured dicts.

## The access layer (`store.py`)

**`Store(database, keys)`** is a frozen dataclass — no scope on the store. Navigation is keys-only: `Store(db)["show"][0][0]` accumulates keys; `__getitem__` appends one. Scope is derived per-operation from the field/dataclass:

- **`read(spec)`** → instance or `None`. A `Fields.*` alias reads one column; a dataclass reads its projected column list, then attaches children recursively. A single-row op requires the full key (`_exact_key_pairs` raises otherwise).
- **`read_or_default(cls)`** → `read` falling back to `cls()`.
- **`read_list(cls)` / `read_dict(cls)`** — one SELECT per scope *level* (not per row), `ORDER BY` remaining key columns, children attached by key prefix. `read_dict` unwraps 1-tuple keys to scalars. Both accept a dataclass or a value-`Field` alias (a standalone scalar map at the root).
- **`write(instance)`** — upserts the flattened row, then per child: delete-scope (FK cascade) + insert the new collection, all in one `transaction()`. Missing trailing keys are derived from the instance's `Key`-annotated attrs. **`write(Fields.x.col, value)`** does a single-column upsert that preserves the row's other columns (partial projection).
- **`write_dict(field, mapping)` / `write_list(field, values)`** — replace a scalar scope wholesale (delete + insert in one transaction).
- **`insert_list(instances)`** — bulk insert with enumerated `idx`, recursing into record children.
- **`delete(cls)`** — deletes rows under the current key prefix; FK `ON DELETE CASCADE` removes descendants.

`_upsert` branches on whether there are non-key values: `on_conflict_do_update(set_=values)` when present, else `on_conflict_do_nothing` (a keys-only / pure-container row has nothing to update). The upsert dialect is dict-dispatched: `UPSERT_INSERT[dialect_name]` → `sqlite_insert` / `postgres_insert`.

## Database, transactions, connections (`database.py`)

**`Database(schema, path=":memory:", single_writer=False, engine=...)`** holds a Core `Engine`.

- **SQLite** is the default: `Database(schema, path="…")`. In-memory uses `StaticPool` + `check_same_thread=False` so one shared connection's schema survives every cross-thread checkout; file SQLite gets `check_same_thread=False` and a `connect` listener setting `foreign_keys=ON` / `busy_timeout` / `journal_mode=WAL`.
- **PostgreSQL** (or any other backend) is supplied by passing a pre-built engine: `Database(schema, engine=create_engine("postgresql+psycopg://…"))`. There is no `url` parameter — `engine=` is the bring-your-own escape hatch, `path=` is the SQLite convenience.

`transaction()` is **thread-local**: the outermost block checks out a connection and `begin()`s; nested blocks compose into it; commit on success, rollback on exception. Reads/writes outside a transaction take a short pooled connection (`reading()` / `writing()`).

Core's column types own all bind/result processing — there is no separate value-marshaling layer. `fetch_one`/`fetch_all` yield `RowMapping`s already decoded by the column types.

## Read cache (`read_cache.py`, opt-in via `single_writer`)

`single_writer=True` builds a `ReadCache` and declares that **no other OS process** writes this DB (true for the serie server, music CLI, keybias script, powerplan). Multiple threads / pooled connections *within* the process are fine — every write funnels through the one `Database`, so it observes them all.

- **Mechanism.** A process-local `write_version` counter; any recorded write bumps it. A read clears the cache when `write_version != cached_version`, then memoizes per key. Result-level granularity: the cache key is `(structural cache key, bound values, explicit params)` from `statement._generate_cache_key()` — this encodes the projection (different dataclasses → different SELECT → different key) **without compiling the statement to a SQL string on every cache hit**. The cached `RowMapping` holds the already-decoded value (the `TypeDecorator` ran before caching), so a consumer codec makes deserialization cheap, not just the fetch.
- **Visibility correctness.** Committed state becomes visible at **commit**, so:
  - Reads **inside a transaction** bypass the cache entirely — they see uncommitted state on the active connection and must neither serve from nor populate the cache shared with other connections (prevents a cross-thread dirty read).
  - An autocommit `run`/`run_many` (outside a transaction) records a write; a transaction records **one** write on **commit**. A transaction that **rolls back** records nothing — the cache only ever holds committed-state reads, so it stays valid.
- **Memory + aliasing.** LRU `OrderedDict`, `CACHE_CAPACITY = 256`, guarded by a lock (serie runs a threaded server). Cached values are returned as **shared references** — the contract is *treat returned values as immutable*. The default `single_writer=False` path holds no cache and takes no lock.

`PRAGMA data_version` is the path to relaxing the single-writer contract to multi-process if ever needed.

## Tables and column types (`tables.py`)

`build_tables(schema)` compiles the registry to a Core `MetaData`. Python→Core type map: `int→Integer, float→Float, str→Text, bytes→LargeBinary, bool→Boolean, datetime/date→native on Postgres, ISO-text `TypeDecorator` on SQLite` (so timezone survives SQLite's typeless storage). Any `Enum` subclass → SQLAlchemy `Enum` (stores the member name). PK = key columns; singleton = `id` PK + `CheckConstraint("id = 1")`; FK = `ForeignKeyConstraint(..., ondelete="CASCADE")` from the inherited key prefix. `create_all(checkfirst=True)` builds the schema.

- **Consumer-registered column types.** `schema.register_column_type(python_type, sql_type)` plugs a consumer `TypeDecorator` in — the same mechanism the built-in `IsoDateTime`/`IsoDate` use. keybias registers a `NumpyArray(TypeDecorator)` so numpy stays out of the library (`sql_type` is held as `Any`; `schema.py` imports no SQLAlchemy). Compression, if any, lives inside the consumer's codec — a `bytes` column is opaque by contract.
- **Indexes.** `schema.index(*field_aliases, where="", unique=False)` — scope derived from the first field; `where` is a raw partial-predicate string (emitted as both `sqlite_where` and `postgresql_where`); `unique` for partial-unique dedup. Alembic `compare_metadata` reflects them without false drift.
- **CHECK constraints.** `schema.check(scope, predicate)` appends a raw-SQL `CheckConstraint` (range / cross-column checks an enum can't express). IN-list checks are modeled as enum columns instead.

## `StoreField` descriptor (`store_field.py`)

A typed read/write view over one scalar field of a `StoreBacked` instance (anything with a `_store: Store`), absorbing the `cast` boilerplate of hand-written getter/setter pairs:

```python
class Storage:
    embeddings = StoreField[NDArray[np.float32]](Fields.sample.embeddings)
    albums_count = StoreField[int](Fields.artist.albums_count, default=0)
```

`__get__` returns `T` (the cast lives once inside the descriptor); a missing value reads back as `default`. Declare `StoreField[X | None](spec)` for a genuinely nullable field, `StoreField[X](spec, default=…)` for one with a fallback. Class-level access returns the descriptor. Not a fit when the store key varies per call — that's a method on a sub-indexed store, not a fixed-field descriptor. For cohesive column groups written together, prefer a partial-projection dataclass + `write(instance)` (one atomic upsert) over N sequential `StoreField` setters.

## Escape hatch (raw SQL)

A consumer can skip `Store` and go straight to the registry + `Database` + `mapping`:

- `instances_from(cls, rows)` — raw `Database.fetch_all(text(...), params)` → typed instances.
- `schema.column(Fields.x.col) -> str` and `schema.table_of(cls) -> str` — name-drift-safe identifiers for hand-written SQL (literals and aggregate structure stay uncoupled).

Escape-hatch SQL goes through the same `Database` (one engine, one transaction), so it shares the cache and transaction semantics. `instance_from` runs an idempotent `coerce(base_type, value)` because raw `text()` yields DBAPI-native scalars (bool as `0`, datetime as ISO string) that the Core-typed `Store` path already decodes.

## Migrations

`Database` **reconciles the live schema with the registry at construction**, desired-state style. Missing tables are created, and purely **additive** drift — new columns, new indexes — is applied in place: NULL reads back as the constructor default (already load-bearing), so an added column is semantically a no-op with nothing to backfill. Adding a field is just editing the `Fields` tree; no migration artifact exists.

Anything non-additive (removed columns, type changes, key changes — a rename diffs as remove + add) makes construction **raise with the pending operations**; handle it with a standalone one-shot script (write, run against the live DB, delete), then restart. Reconciliation is all-or-nothing: no additive op is applied while a blocked op is pending, so the add half of a rename cannot land without the data move.

`migrations.schema_diff(database)` (Alembic `compare_metadata`) computes the pending ops and remains the standalone drift check. It compares only tables the registry owns, so foreign tables sharing the database are ignored — which also means a scope *removed* from the registry is not detected; dropping its table is a one-shot script. On SQLite, a 31-bit fingerprint of the compiled DDL stored in `PRAGMA user_version` skips reconciliation (and the alembic import) entirely when nothing changed — the steady-state startup is a single PRAGMA read, cheaper than the previous unconditional `create_all(checkfirst=True)` reflection. Other backends reconcile every startup.

## Key operational constraints

- **NULL → constructor defaults** is load-bearing — every storage dataclass field must have a default. A single-`Field` read returns `None` on an absent row (the default rule applies to *dataclass* reads); consumers wanting a fallback use `StoreField(..., default=…)` or `read(...) or default`.
- **Cascade-reset value objects** (e.g. serie's `CheckPoint`): setters that must clear dependent fields go through a full-dataclass `write(CheckPoint(...))`, not single-column writes — flattening would break the cascade.
- **FK parent/child encodes a write-ordering dependency.** Model a scope as a child (FK) only when the parent row is guaranteed to exist first; co-keyed entities written independently or out of order must be **sibling top-level scopes** sharing the key, not parent/child.

## Not yet implemented

- **Cross-scope projection dataclasses.** Today `scope_of_dataclass` assumes every field of a dataclass lives in one scope (true for all current consumers). The general form partitions the dataclass's fields by scope, treats the deepest-key scope as row identity, and reads one SELECT per scope merged by key prefix (a join only when per-scope round-trips actually matter). The per-field `Field` annotation is what makes this possible. **Open question before implementing:** do a dataclass's scopes always lie on one root-to-node ancestor chain (clean prefix nest → simple merge), or can they pull from sibling scopes off different key paths (forces real FK-driven joins)?
- **Auto-rowid event tables** (keyless, append-only). Designed (explicit `kind` at registration, typed `append`, reads via the escape hatch) but unbuilt — powerplan's `sessions` turned out to have a natural key (`started_at`), so no consumer needs it yet.
- **Column-value cache granularity** — would let two projections reading the same blob column share one decode; result-level re-decodes per distinct statement. Land only if profiling shows the re-decode matters.
