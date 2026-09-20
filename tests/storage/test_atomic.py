from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from package_utils.storage import Store, atomic

from .fields import Node

if TYPE_CHECKING:
    from package_utils.storage import Database


class Catalog:
    def __init__(self, store: Store) -> None:
        self._store = store

    @atomic
    def add_pair(self, first: str, second: str, *, fail: bool = False) -> None:
        self._store.write(Node(key=first))
        if fail:
            message = "boom"
            raise RuntimeError(message)
        self._store.write(Node(key=second))


def test_atomic_commits_all_writes(db: Database) -> None:
    Catalog(Store(db)).add_pair("a", "b")
    keys = [node.key for node in Store(db).read_list(Node)]
    assert keys == ["a", "b"]


def test_atomic_rolls_back_on_failure(db: Database) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        Catalog(Store(db)).add_pair("a", "b", fail=True)
    assert Store(db).read_list(Node) == []
