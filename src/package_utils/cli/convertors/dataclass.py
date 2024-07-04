import functools
import inspect
import typing
from collections.abc import Callable, Iterator
from dataclasses import MISSING, Field, dataclass, fields
from typing import Any, TypeVar

from . import class_
from .parameter import CliParameter

T = TypeVar("T")


@dataclass
class Convertor(class_.Convertor[T]):
    object: type[T]

    def create_cli_entry_method(self) -> Callable[..., T]:
        @functools.wraps(self.annotated_method)
        def wrapped_method(*args: Any, **kwargs: Any) -> Any:
            specified_kwargs = {k: v for k, v in kwargs.items() if v is not None}
            return self.object(*args, **specified_kwargs)

        wrapped_method.__doc__ = self.object.__doc__
        return typing.cast(Callable[..., T], wrapped_method)

    def extract_parameters_info(self) -> Iterator[CliParameter]:
        for field in fields(self.object):  # type: ignore[arg-type]
            if field.init:
                yield self.create_cli_parameter(field)

    def create_cli_parameter(self, field: Field[Any]) -> CliParameter:
        no_default = field.default is MISSING
        default = None if no_default else field.default
        parameter = inspect.Parameter(
            field.name,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=default,
            annotation=field.type,
        )
        annotation = self.annotations[field.name]
        if no_default:
            annotation = annotation | None
        return CliParameter(parameter, annotation)
