import inspect
import sys
from collections.abc import Callable
from dataclasses import dataclass, is_dataclass
from typing import Any, Generic, TypeVar, cast

import typer

from package_utils.annotations import first_parameter_types

from . import convertors

T = TypeVar("T")


@dataclass
class EntryPoint(Generic[T]):
    method: Callable[..., T]
    argument_class: type[Any] | None = None

    def __call__(self) -> T:
        self.setup_argument_class()
        if self.argument_class is None:
            result = run_with_cli_args(self.method)
        else:
            instance = run_with_cli_args(self.argument_class)
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
        types = first_parameter_types(self.method)
        classes = (type_ for type_ in types if is_dataclass(type_))
        self.argument_class = next(classes, None)


def run_with_cli_args(object_: Callable[..., T] | type[T]) -> T:
    is_dataclass_ = is_dataclass(object_)
    module = convertors.dataclass if is_dataclass_ else convertors.method
    cli_entry_method = module.Convertor(object_).run()
    app = typer.Typer(add_completion=False)
    app.command()(cli_entry_method)
    result_or_exit_code = app(standalone_mode=False)
    if isinstance(result_or_exit_code, int):
        sys.exit(result_or_exit_code)
    return cast("T", result_or_exit_code)
