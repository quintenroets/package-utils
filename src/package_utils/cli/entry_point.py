import inspect
import sys
from collections.abc import Callable
from dataclasses import MISSING, Field, dataclass, fields, is_dataclass
from typing import Any, Generic, TypeVar, cast

from package_utils.annotations import first_parameter_types

from .convertors.parameter import TyperMarker, extract_dataclass, resolve_annotations

T = TypeVar("T")


@dataclass
class EntryPoint(Generic[T]):
    method: Callable[..., T]
    argument_class: type[Any] | None = None

    def __call__(self) -> T:
        self.setup_argument_class()
        if self.argument_class is None:
            result = instantiate(self.method)
        else:
            instance = instantiate(self.argument_class)
            result = self.method(instance)
        return result

    def setup_argument_class(self) -> None:
        if self.argument_class is None and inspect.isfunction(self.method):
            self.extract_argument_class()
        if self.argument_class is not None:
            method_doc = self.method.__doc__
            if method_doc is not None:
                self.argument_class.__doc__ = method_doc

    def extract_argument_class(self) -> None:
        argument_class = next(first_parameter_types(self.method), None)
        if is_dataclass(argument_class):
            self.argument_class = argument_class


def instantiate(object_: Callable[..., T] | type[T]) -> T:
    return (
        cast("type[T]", object_)()
        if defaults_cover_arguments(object_)
        else run_with_cli_args(object_)
    )


def run_with_cli_args(object_: Callable[..., T] | type[T]) -> T:
    from .cli_runner import Runner

    return Runner(object_).run_with_cli_args()


def defaults_cover_arguments(object_: Callable[..., Any] | type[Any]) -> bool:
    """
    Report whether a bare invocation can be served without building the parser.

    Building it imports typer — tens of milliseconds, more than a fast command's
    entire run — while an invocation with nothing to parse only ever yields the
    defaults the dataclass already declares.

    The saving only materializes for a caller that defers its own typer import too:
    an eager one at the top of the argument model loads the package before this ever
    runs. Resolving against a stub is what lets such a model be read here at all.

    A nested dataclass disqualifies the class: its fields are flattened into
    separate arguments and reassembled by dacite from *their* defaults, so the
    outer default never applies and direct instantiation would not agree.
    """
    return (
        not sys.argv[1:]
        and isinstance(object_, type)
        and is_dataclass(object_)
        and all(is_defaulted(field_) for field_ in fields(object_))
        and all(
            extract_dataclass(annotation) is None
            for annotation in resolve_annotations(object_, TyperMarker()).values()
        )
    )


def is_defaulted(field_: Field[Any]) -> bool:
    has_default = field_.default is not MISSING or field_.default_factory is not MISSING
    return has_default or not field_.init
