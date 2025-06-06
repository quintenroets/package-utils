from __future__ import annotations

import typing
from dataclasses import asdict
from typing import Any, TypeVar

import dacite
from typing_extensions import Self

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover

T = TypeVar("T")


class SerializationMixin:
    @classmethod
    def from_dict(
        cls,
        items: dict[str, Any],
        config: dacite.Config | None = None,
    ) -> Self:
        if config is None:
            config = dacite.Config(strict=True)
        return dacite.from_dict(cls, items, config=config)

    def dict(self: DataclassInstance) -> dict[str, Any]:
        return asdict(self)
