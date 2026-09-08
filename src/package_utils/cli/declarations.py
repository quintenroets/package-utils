import sys
from collections.abc import Callable
from functools import cache, partial
from inspect import Parameter, signature
from types import SimpleNamespace
from typing import Any

from package_utils.annotations import metadata_of


def declared_parameters(object_: Callable[..., Any]) -> list[Parameter]:
    globals_ = create_deferred_namespace() | vars(sys.modules[object_.__module__])
    signature_ = signature(object_, eval_str=True, globals=globals_)
    return list(signature_.parameters.values())


@cache
def create_deferred_namespace() -> dict[str, Any]:
    stubs = {name: partial(DeferredInfo, name) for name in ("Argument", "Option")}
    return {"typer": SimpleNamespace(**stubs)} | stubs


def resolvable_without_parser(parameter: Parameter) -> bool:
    return parameter.default is not Parameter.empty and all(
        declaration.is_value_neutral
        for declaration in metadata_of(parameter.annotation)
        if isinstance(declaration, DeferredInfo)
    )


class DeferredInfo:
    VALUE_NEUTRAL_SETTINGS = frozenset(
        {
            "help",
            "hidden",
            "metavar",
            "rich_help_panel",
            "show_choices",
            "show_default",
            "show_envvar",
        }
    )

    def __init__(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.name = name
        self.args = args
        self.kwargs = kwargs

    @property
    def is_value_neutral(self) -> bool:
        return self.kwargs.keys() <= self.VALUE_NEUTRAL_SETTINGS
