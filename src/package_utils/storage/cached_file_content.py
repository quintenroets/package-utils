import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from superpathlib import Path

T = TypeVar("T")
Self = TypeVar("Self", bound="CachedFileContent[Any]")


@dataclass
class CachedFileContentRead(Generic[T]):
    path: Path
    default: T = field(default_factory=dict)  # type: ignore[assignment]
    mtime: float | None = None
    content: T | None = None
    load_function: Callable[[Any], T] | None = None

    def __call__(self, instance: Any) -> T:
        return self.__get__(instance)

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> T:
        return self.get(instance)

    def get(self, instance: Any) -> T:
        if self.content is None or self.file_content_changed:
            self.mtime = self.path.mtime
            if self.load_function is None:
                self.content = self.load()
            else:
                self.content = self.load_function(instance)
            if not self.content and self.default is not None:
                self.content = self.default
        return self.content

    @property
    def file_content_changed(self) -> bool:
        return self.mtime is None or self.mtime < self.path.mtime

    def load(self) -> T:
        content = self.path.yaml
        return typing.cast(T, content)


@dataclass
class CachedFileContent(CachedFileContentRead[T]):
    save_function: Callable[[Any, T], None] | None = None

    def __set__(self, instance: Any, value: T) -> None:
        return self.set(instance, value)

    def set(self, instance: Any, value: T) -> None:
        self.content = value
        if self.save_function is None:
            self.save(value)
        else:
            self.save_function(instance, value)
        self.mtime = self.path.mtime

    def save(self, content: T) -> None:
        self.path.yaml = typing.cast(dict[str, str], content)

    def setter(self: Self, function: Callable[[Any, T], None]) -> Self:
        self.save_function = function
        return self


def cached_path_property(
    path: Path,
    default: Any = None,
) -> Callable[[Callable[[Any], T]], CachedFileContent[T]]:
    def decorator(function: Callable[[Any], T]) -> CachedFileContent[T]:
        return CachedFileContent(path, load_function=function, default=default)

    return decorator


def cached_path_dict_property(
    path: Path,
) -> Callable[[Callable[[Any], T]], CachedFileContent[T]]:
    def decorator(function: Callable[[Any], T]) -> CachedFileContent[T]:
        default = typing.cast(T, {})
        return CachedFileContent(path, load_function=function, default=default)

    return decorator
