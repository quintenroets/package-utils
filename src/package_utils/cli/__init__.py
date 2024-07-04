from typing import TypeVar

from .entry_point import EntryPoint as create_entry_point  # noqa: N813

T = TypeVar("T")

__all__ = ["create_entry_point", "instantiate_from_cli_args"]


def instantiate_from_cli_args(_class: type[T], documented_object: object = None) -> T:
    if documented_object is not None:
        _class.__doc__ = documented_object.__doc__
    instantiate_entry_point = create_entry_point(_class)
    return instantiate_entry_point()
