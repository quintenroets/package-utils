from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Option(Enum):
    read = "read"
    write = "write"


@dataclass
class Options:
    mode: Option = Option.read
