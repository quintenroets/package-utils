import dataclasses
import functools
import inspect
import typing
from collections.abc import Callable, Iterator
from dataclasses import MISSING, Field, dataclass, field, fields
from typing import TYPE_CHECKING, Any, TypeVar

from . import method
from .parameter import CliParameter

if TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover


T = TypeVar("T")


@dataclass
class Convertor(method.Convertor[T]):
    object: type[T]
    name_prefix: str = ""
    argument_prefixes: dict[str, str] = field(default_factory=dict)

    def create_cli_entry_method(self) -> Callable[..., T]:
        @functools.wraps(self.annotated_method)
        def wrapped_method(**kwargs: Any) -> Any:
            specified_kwargs = {k: v for k, v in kwargs.items() if v is not None}
            if self.argument_prefixes:
                import dacite  # noqa: PLC0415

                self.unflatten(specified_kwargs)
                config = dacite.Config(strict=True)
                result = dacite.from_dict(self.object, specified_kwargs, config=config)
            else:
                result = self.object(**specified_kwargs)
            return result

        wrapped_method.__doc__ = self.object.__doc__
        return typing.cast("Callable[..., T]", wrapped_method)

    def unflatten(self, items: dict[str, Any]) -> None:
        while flattened_names := items.keys() & self.argument_prefixes.keys():
            for name in flattened_names:
                prefix = self.argument_prefixes[name]
                nested_name = name.removeprefix(prefix + "_")
                items.setdefault(prefix, {})[nested_name] = items.pop(name)

    def extract_parameters_info(self) -> Iterator[CliParameter]:
        for field_ in fields(self.object):  # type: ignore[arg-type]
            if field_.init:
                yield from self.extract_field_parameters(field_)

    def extract_field_parameters(self, field_: Field[Any]) -> Iterator[CliParameter]:
        parameter = self.create_cli_parameter(field_)
        dataclass_ = self.extract_dataclass(parameter)
        if dataclass_ is None:
            yield parameter
        else:
            yield from self.generate_recursive_parameters(parameter, dataclass_)

    def generate_recursive_parameters(
        self,
        parameter: CliParameter,
        dataclass_: "type[DataclassInstance]",
    ) -> Iterator[CliParameter]:
        name = parameter.parameter.name
        convertor = Convertor(dataclass_, name_prefix=f"{name}_")
        for nested_parameter in convertor.extract_parameters_info():
            self.argument_prefixes[nested_parameter.parameter.name] = name
            yield nested_parameter

    def create_cli_parameter(self, field_: Field[Any]) -> CliParameter:
        annotation = self.annotations[field_.name]
        parameter = inspect.Parameter(
            self.name_prefix + field_.name,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=None if field_.default is MISSING else field_.default,
        )
        return CliParameter(parameter, annotation)

    @classmethod
    def extract_dataclass(
        cls,
        parameter: CliParameter,
    ) -> "type[DataclassInstance]|None":
        types = (
            type_
            for type_ in parameter.extract_types()
            if dataclasses.is_dataclass(type_)
        )
        return typing.cast("type[DataclassInstance]|None", next(types, None))
