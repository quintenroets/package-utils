from typing import TYPE_CHECKING, Any

from .atomic import StoreBacked, atomic
from .cached_file_content import (
    CachedFileContent,
    cached_path_dict_property,
    cached_path_property,
)
from .database import Database
from .mapping import assign_path, instance_from, instances_from
from .read_cache import ReadCache
from .schema import Field, Key, Schema, Scope
from .store import Store
from .store_field import StoreField
from .tables import SchemaTables, build_tables

if TYPE_CHECKING:
    from .migrations import schema_diff


def __getattr__(name: str) -> Any:
    # defer alembic (only needed to run migrations) out of the import path
    if name == "schema_diff":
        from .migrations import schema_diff  # noqa: PLC0415

        return schema_diff
    raise AttributeError(name)
