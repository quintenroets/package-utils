import typing
from dataclasses import dataclass
from typing import Generic, TypeVar

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover

Options = TypeVar("Options", bound="DataclassInstance")
Config = TypeVar("Config", bound="DataclassInstance")
Secrets = TypeVar("Secrets", bound="DataclassInstance")


@dataclass
class Models(Generic[Options, Config, Secrets]):
    Options: type[Options] | None = None
    Config: type[Config] | None = None
    Secrets: type[Secrets] | None = None
