# Storage Library — Decision Log

History and rationale behind [generic-storage-library.md](generic-storage-library.md). The companion doc describes the **current** design; this one records how it got there, what was tried and reversed, and what must **not** be re-proposed or re-litigated. Where the two conflict, the current-design doc wins — entries here are dated context.

## 2026-07-06 — startup schema reconciliation (additive auto-migration)

The NULL→default invariant ("every storage dataclass field must have a default") makes an added column semantically free — NULL already means constructor default, so there is never anything to backfill. Exploited: `Database` now reconciles the live schema at construction, applying additive drift (new tables/columns/indexes) in place and **raising** on anything non-additive, which stays a standalone one-shot script. All-or-nothing so the add half of a rename can't land without the data move. A 31-bit DDL fingerprint in SQLite's `PRAGMA user_version` gates the whole path — steady-state startup is one PRAGMA read, and alembic is only imported when the fingerprint changes. `schema_diff` now filters to registry-owned tables (`include_name`), so shared databases and tooling tables don't block construction; the cost is that a scope removed from the registry is no longer detected.

> Supersedes the "versioned Alembic history per consumer" story: none of the four consumers ever created a `migrations/` directory or called `schema_diff` — three weeks of real fleet evolution were handled by hand-run one-shot scripts, evidence the per-consumer Alembic env was the wrong abstraction at this scale.

## 2026-06-27 — read cache: dirty-read + stale-after-commit fix

The `single_writer` read cache treated *write submission* as the visibility boundary, which is wrong for concurrent readers (serie's threaded server). Two latent bugs:

- **Cross-thread dirty read.** A read *inside* a transaction went through the cache and populated it with uncommitted state; another thread could then read that uncommitted value from the shared cache before commit (or after rollback, until the rollback bump landed).
- **Stale after commit.** `record_write` bumped on every `run` (write submission) and on rollback, but **not on commit**. An out-of-transaction reader caching the pre-commit committed state at the post-write version would keep being served that stale value after the transaction committed, since nothing bumped at commit.

Both stem from one root: committed state becomes visible at **commit**, not at write. Fix:
- Reads bypass the cache while `active_connection is not None` (in a transaction) — in-txn reads see uncommitted state and must neither serve from nor populate the shared cache.
- A write records the version bump at its **commit boundary**: autocommit `run`/`run_many` bump (they commit immediately); a transaction bumps **once on commit**. Rollback no longer bumps — with the bypass, the cache only ever holds committed-state reads, so a rollback (which changes no committed state) leaves it valid.

Covered by `test_concurrent_reader_sees_neither_uncommitted_nor_stale` (a file-DB two-thread test; an in-memory `StaticPool` would share one connection and hide the isolation). Same change dropped the unused `Database.url` parameter — every consumer constructs with `path=` (SQLite) and Postgres comes in via `engine=`, so `url=` was a redundant third spelling. `cache_key` switched from `str(statement.compile())` (compiled the SQL string on every cache hit) to `statement._generate_cache_key()` (structural key + bound values, no string compilation).

## 2026-06-17 — read cache + consumer-registered column types

Replaced the original `total_changes`-based cache idea. **"Statelessness" was never a standalone rule** — it appears in exactly one decision (adopting SQLAlchemy *Core*, rejecting the *ORM*: no identity map / unit-of-work / lazy loading). What it guarantees is **read freshness** and **value-semantics domain objects**. A result cache with invalidation is *not* an identity map and is compatible with the design as long as it preserves freshness; the only real obstacle was invalidation correctness.

- **`single_writer` flag.** The old `total_changes` cache was sound only because `Database` funneled all access through one connection + RLock. The Core engine is pooled / possibly multi-process, so a generic result cache is unsound there. `single_writer=True` declares no other OS process writes this DB (true for every consumer); under it a process-local write-version counter (bumped on each write, any write busts the whole cache) is both sound and simpler than `total_changes`.
- **Codec/cache split.** Caching the `bytes → ndarray` decode does **not** force numpy into the library: the **codec** is a consumer-supplied `TypeDecorator` (`Schema.register_column_type`), the **cache** sits above result-processing and caches whatever the processor produced with zero numpy knowledge. The library owns the caching *mechanism*; the consumer owns the *codec*. A library cache beats an app `cached_property` because only the library knows when the cache is wrong (it maintains the write-version) — a correctness argument, not just DRY.
- **Compression stays codec-side**, never a generic column option — a `bytes` column is opaque, and the codec choice (zlib/zstd/blosc-shuffle) is data-specific. `np.save` does zero compression but is the correct serialization default (lossless on shape+dtype, atomic); reach for blosc/zstd only after measuring.

## 2026-06-18 — powerplan prerequisites

Four additive features landed together (serie needed no changes):
- **Flat composite business keys** — `Schema.scope` keeps **every** `Key()` in a namespace (was first-only), in declaration order, as PK + FK prefix. `inherited_keys` renames all of a parent's own keys, splitting own-vs-inherited via `len(parent.parent.key_columns)`. Targets: powerplan's `lift_targets`/`run_targets`/`supersets`/`vitals` — flat leaf scopes that would be grotesque to nest. The single-own-key path (serie/music) is byte-identical.
- **Indexes (incl. partial)** and **CHECK constraints** — see current-design doc. CHECK was the one "accepted loss" candidate that turned out near-free (a per-scope raw-SQL predicate, sibling of the index feature), so it was added rather than documented as a loss.
- **Escape-hatch one-liners** `schema.column` / `schema.table_of`.
- **1:1 satellites — "composes for free" was false; fixed.** powerplan's `cardio_metrics` is a keyless 1:1 satellite of `sessions`. `Schema.scope` had dropped a parented keyless scope's inherited keys, so the satellite came out with no PK and a malformed empty FK. Fix: `keyed = bool(keys) or parent is not None`. The Store paths needed no change (the satellite dataclass carries zero `Key` attrs; navigation supplies the key).

## 2026-06-16 — music migration (first non-serie consumer)

`../music` ported off YAML/`CachedFileContent`. The real test of the collection-mapper predictions; nearly everything worked unmodified.
- **One library bug, one fix.** A standalone keys-only / pure-container upsert (`store[k].write(Record())` with no non-key columns) died on `on_conflict_do_update(set_={})`. The pure-container support had only ever been exercised through whole-tree writes (the `insert()` path), never the upsert path. Fix: `_upsert` branches to `on_conflict_do_nothing` when there are no values. **This was the only library code change the entire migration needed.**
- **FK encodes write-ordering** — `artist_info` shares the artist's `id` but is written *before* the `artist` row, so it is a sibling top-level scope, not a child. Rule promoted to the current-design doc.
- **Single-field cross-write** — `albums_count` lives on the `artist` row but is written alone; the partial upsert must preserve `name`/`type_`.
- **JSON column re-rejected** — `artist_info` is only ever stored/read wholesale, but structured data still flattens to typed scopes (uniformity, drift detection, queryability). App-layer serialization is for opaque binary only.
- **Consumer sharp edges** — a domain enum used as a column type must live where `fields.py` can import it without a cycle (music defines `ArtistType` in `fields.py`, re-exports from `models`).

## 2026-06-15 — migration to SQLAlchemy Core

The day-old bespoke `Dialect`/`Backend` layer (below) was the right call *while Postgres was only a conformance fixture*. Once Postgres became a real product the calculus flipped: real multi-backend correctness (paramstyle, quoting, type edge cases, upsert dialects, **connection pooling**) is exactly Core's job, and the bespoke `Database`'s single-connection / RLock / `total_changes` model was SQLite-single-writer-shaped and wrong for a pooled client-server DB. Decision was an explicit user call after debate.

**Adopted Core only, not the ORM** (no Session / identity map / unit-of-work — value semantics still holds). **What stayed:** the registry, `Store` navigation, projection dataclasses, recursive tree read/write — the public API was unchanged, so serie needed no app changes. **What changed at/below the SQL:** `tables.py` compiles the registry to a Core `MetaData`; `database.py` holds an Engine + pool + thread-local transaction; `store.py` uses Core constructs + dialect-dispatched upsert; value marshaling moved onto Core's column types. The `total_changes` read cache was dropped (later replaced — see 2026-06-17). **Alembic** (`migrations.py`) became the production migration + drift-detection path. The same migration also generalized the **collection mapper** (dict-keyed + scalar children, pure-container records, standalone scalar maps) and added **enum columns**.

## 2026-06-13 — Dialect + Backend abstraction (SUPERSEDED 2026-06-15)

> Historical. This bespoke layer lived for two days and was deleted when Core landed; `dialect.py`/`backend.py`/`postgres_backend.py` no longer exist. Kept for the reasoning that carried into Core's type choices.

Factored SQLite-specific concerns into two value objects so a second backend could prove the abstraction real (Postgres as conformance fixture): `Dialect` (SQL text + value marshaling — `sql_types`, serializers, `table_options` like `STRICT`) and `Backend` (driver/connection mechanics). Paramstyle was a Backend concern (`translate` adapts `?`→`%s` at the execution boundary). The live conformance run caught a real SQLite-shaped leak: the hard-coded `STRICT` table suffix, which Postgres rejected — exactly what the fixture exists to expose. Lesson carried forward: native-vs-ISO datetime, `STRICT` incompatibility with Core's type-affinity rendering on SQLite, and "what actually varies per database" all informed the Core type map.

## 2026-06-13 — extraction into `package_utils.storage`

The generic machinery moved out of serie (its testbed) into the library; serie became the first consumer. The prerequisite was already met: the registry is a value object (`Schema`) carried by `Database(schema)`, no module-global registry. **Explicit registration is the final form** (`schema.scope(Fields.serie, parent=…)`) — not a stepping stone. `singleton` is derived (no key + no parent). The generic round-trip test suite (random nested dataclass trees) caught one latent bug: `serialize`/`deserialize` must skip `None`.

## Rejected alternatives (do not re-propose)

- **EAV God-table; flat-string keys; full tree normalization up front; scope-on-field; explicit-scope navigation; sharing one field across scopes; depth-inference of scope; flat field registry with hand-written column names; JSON blob for nested records** (replaced by flattened prefixed columns); **`read_all(Field)`** (subsumed by key fields + `read_list`); **three separate `Fields`/`Keys`/`Types` declarations** (replaced by the single merged `Fields` tree where each column is one `Annotated[python_type, Field()|Key()]`).
- **An existing ORM (SQLAlchemy ORM / SQLModel / peewee / sqlite-utils).** Core was **adopted 2026-06-15**; the **ORM tier remains rejected**: the design is deliberately value-semantic (assembled-on-read / scattered-on-write, no identity map / unit-of-work / lazy loading), the inverse of the ORM's Session model. Core compiles the `MetaData` and binds typed `select/insert/delete`; key-prefix `[]` navigation stays ~20 lines of sugar on top, viable only because the schema *is* a strict ancestor-key tree (an assumption a general ORM can't make).
- **Schema derived from the dataclasses** (deleting the `Fields` tree) — dataclasses are partial *projections*; the canonical union schema can't live in any single one. **Nested-scope `Fields` tree** — name-binding collision between scalar pointer *columns* and scope *classes*; sibling scopes keep column and table namespaces apart for free. **Topology via marker base** (`class season(ChildOf[serie])`) — fake-inheritance metadata smuggling plus a walk-rule table to replace four explicit registration lines. Explicit registration wins.
- **Composite OWN keys forced by flat modeling for music** — proven unnecessary (music's scopes nest as single-own-key levels). Flat composites *did* land for powerplan (2026-06-18), where nesting would be grotesque.

## Naming decisions (do not re-litigate)

- **The consumer's declaration is named `Fields`** — after the domain concept (fields), not the Python mechanism (`Types`: the leaves are storage-neutral field declarations, not type aliases) nor the storage form (`Columns`: a field may land as one column, a flattened prefix group, or a child table). Same rule names the markers `Field`/`Key` (domain roles), not `Type`/`Column`.

## Superseded backlog items

- **Schema drift detection** — landed via Alembic `compare_metadata` (`migrations.schema_diff`).
- **Read cache** — landed 2026-06-17 (single_writer), corrected 2026-06-27 (commit-boundary invalidation).
- **Bool coercion on single-Field reads** — closed by the adapter/`coerce` layer applied symmetrically on read.
- **Auto-rowid event tables** — designed but **not built**: powerplan keys `sessions` on `started_at` (a genuine natural key), so the surrogate-id append-only kind has no consumer. Retained as a design for a genuinely keyless future consumer.
- **PEP 747 `TypeForm[T]`** — would type `read(Fields.serie.position)` as `float | None` and delete the call-site `cast`s; adopt when mypy support lands.

## Worked negative example — `../revnets` (assessed 2026-06-19, NOT migrated)

Its disk state is (1) write-once `results.yaml` dumps nothing reads back, (2) `torch.save` weights + pickled caches (large binary), (3) input `config.yaml`. None of the three fit-criteria hold — adopting the library would *add* ceremony to replace a one-line `path.yaml = {...}` write. The library fits serie/music/powerplan/keybias because they had real persistence complexity; revnets doesn't.
