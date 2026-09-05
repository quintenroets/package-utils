from __future__ import annotations

from dataclasses import dataclass

from superpathlib import Path


@dataclass
class Options:
    debug: bool = False
    config_path: Path = Path.draft


@dataclass
class Config:
    output_path: Path | None = None


@dataclass
class ApiSecrets:
    id: str
    token: str


@dataclass
class Secrets:
    token: str
    api: ApiSecrets
