from typing import TypeVar

from .entry_point import EntryPoint as create_entry_point

T = TypeVar("T")

__all__ = ["create_entry_point", "instantiate_from_cli_args"]


def instantiate_from_cli_args(_class: type[T]) -> T:
    instantiate_entry_point = create_entry_point(_class)
    return instantiate_entry_point()
