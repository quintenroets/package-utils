from importlib import import_module
from typing import TYPE_CHECKING, Any

from .atomic import StoreBacked, atomic
from .cached_file_content import (
    CachedFileContent,
    cached_path_dict_property,
    cached_path_property,
)
from .mapping import assign_path, instances_from
from .read_cache import ReadCache
from .schema import Field, Key, Schema, Scope
from .store_field import StoreField

if TYPE_CHECKING:
    from .database import Database
    from .migrations import schema_diff
    from .store import Store
    from .tables import SchemaTables, build_tables

# keep sqlalchemy (only needed once a database is used) and alembic (only needed to
# run migrations) out of the import path
DEFERRED_MODULES = {
    "Database": ".database",
    "SchemaTables": ".tables",
    "Store": ".store",
    "build_tables": ".tables",
    "schema_diff": ".migrations",
}


def __getattr__(name: str) -> Any:
    if name in DEFERRED_MODULES:
        return getattr(import_module(DEFERRED_MODULES[name], __package__), name)
    raise AttributeError(name)
