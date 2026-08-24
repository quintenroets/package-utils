from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class VariableLengthTuple:
    numbers: tuple[int, ...] = ()


@dataclass
class Dictionary:
    values: dict[str, str] = field(default_factory=dict)


@dataclass
class Function:
    hook: Callable[[int], str] = str
