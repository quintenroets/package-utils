from __future__ import annotations

from typing import TYPE_CHECKING

from package_utils.storage import Store, StoreField

from .fields import Fields

if TYPE_CHECKING:
    from package_utils.storage import Database


class Preferences:
    theme = StoreField[str](Fields.setting.value)
    label = StoreField[str](Fields.setting.value, default="untitled")

    def __init__(self, store: Store) -> None:
        self._store = store


def test_store_field_round_trips(db: Database) -> None:
    preferences = Preferences(Store(db))
    preferences.theme = "dark"
    assert preferences.theme == "dark"


def test_store_field_falls_back_to_default(db: Database) -> None:
    assert Preferences(Store(db)).label == "untitled"


def test_store_field_class_access_returns_descriptor() -> None:
    assert Preferences.theme.spec is Fields.setting.value
