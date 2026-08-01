from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

CACHE_CAPACITY = 256


@dataclass
class ReadCache:
    """LRU cache of read results, invalidated whenever a write is recorded.

    `record_write` bumps a version that clears the cache on the next read, so
    the cache is only sound under a single writer (an external writer would not
    bump it). `Database` holds one only when `single_writer` is set.
    """

    capacity: int = CACHE_CAPACITY
    entries: OrderedDict[Any, Any] = field(default_factory=OrderedDict)
    lock: threading.Lock = field(default_factory=threading.Lock)
    write_version: int = 0
    cached_version: int = -1

    def record_write(self) -> None:
        with self.lock:
            self.write_version += 1

    def fetch(self, key: Any, read: Callable[[], Any]) -> Any:
        with self.lock:
            if self.write_version != self.cached_version:
                self.entries.clear()
                self.cached_version = self.write_version
            if key in self.entries:
                self.entries.move_to_end(key)
            else:
                self.entries[key] = read()
                if len(self.entries) > self.capacity:
                    self.entries.popitem(last=False)
            return self.entries[key]
