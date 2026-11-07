from __future__ import annotations

import typing
from dataclasses import asdict
from pathlib import Path
from typing import Any, Self

import dacite
from dacite import Config

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover

default_config = Config(strict=True, cast=[Path])


class SerializationMixin:
    @classmethod
    def from_dict(cls, items: dict[str, Any], config: Config = default_config) -> Self:
        return dacite.from_dict(cls, items, config=config)

    def dict(self: DataclassInstance) -> dict[str, Any]:
        return asdict(self)
