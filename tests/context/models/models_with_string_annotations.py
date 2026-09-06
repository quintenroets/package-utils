from __future__ import annotations

from dataclasses import dataclass, field
from secrets import token_hex

from superpathlib import Path


@dataclass
class Options:
    debug: bool = False
    config_path: Path = Path.draft


@dataclass
class Config:
    output_path: Path | None = None


@dataclass(frozen=True)
class ApiSecrets:
    id: str
    token: str


@dataclass(frozen=True)
class DefaultedSecrets:
    label: str = "default"
    token: str = field(default_factory=token_hex)


@dataclass
class Secrets:
    token: str
    api: ApiSecrets
    optional_api: ApiSecrets | None
    defaulted: DefaultedSecrets
    password: str = field(repr=False)
