from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

if TYPE_CHECKING:
    from .atomic import StoreBacked

T = TypeVar("T")


class StoreField(Generic[T]):
    """Typed read/write view over a single field of a `StoreBacked` instance's store.

    A missing value reads back as ``default``, so declare ``StoreField[int](spec,
    default=0)`` for a non-optional field and ``StoreField[int | None](spec)`` for
    a nullable one.
    """

    def __init__(self, spec: Any, default: T | None = None) -> None:
        self.spec = spec
        self.default = default

    @overload
    def __get__(self, instance: None, owner: type | None = None) -> StoreField[T]: ...
    @overload
    def __get__(self, instance: StoreBacked, owner: type | None = None) -> T: ...
    def __get__(
        self,
        instance: StoreBacked | None,
        owner: type | None = None,
    ) -> StoreField[T] | T:
        return self if instance is None else self.read_value(instance)

    def read_value(self, instance: StoreBacked) -> T:
        value = instance._store.read(self.spec)  # noqa: SLF001
        return cast("T", self.default if value is None else value)

    def __set__(self, instance: StoreBacked, value: T) -> None:
        instance._store.write(self.spec, value)  # noqa: SLF001
