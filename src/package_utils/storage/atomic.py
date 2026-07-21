from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Concatenate, ParamSpec, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from .store import Store

P = ParamSpec("P")
R = TypeVar("R")


class StoreBacked(Protocol):
    _store: Store


S = TypeVar("S", bound=StoreBacked)


def atomic(
    method: Callable[Concatenate[S, P], R],
) -> Callable[Concatenate[S, P], R]:
    @wraps(method)
    def wrapper(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
        with self._store.transaction():
            return method(self, *args, **kwargs)

    return cast("Callable[Concatenate[S, P], R]", wrapper)
