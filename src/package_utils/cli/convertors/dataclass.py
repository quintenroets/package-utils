import dataclasses
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from inspect import Parameter
from typing import TYPE_CHECKING, Any, TypeVar

from . import method
from .parameter import extract_types, resolve_type

if TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover


T = TypeVar("T")


@dataclass
class Convertor(method.Convertor[T]):
    object: type[T]
    name_prefix: str = ""
    may_be_absent: bool = False

    def create_kwargs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return dict(self.generate_kwargs(arguments))

    def generate_kwargs(self, arguments: dict[str, Any]) -> Iterator[tuple[str, Any]]:
        for field_name, convertor in self.convertors.items():
            value = convertor.create_value(arguments)
            if value is not None:
                yield field_name, value

    def create_value(self, arguments: dict[str, Any]) -> T | None:
        kwargs = self.create_kwargs(arguments)
        absent = self.may_be_absent and not kwargs
        return None if absent else self.object(**kwargs)

    def extract_parameters(self) -> Iterator[Parameter]:
        for convertor in self.convertors.values():
            yield from convertor.extract_parameters()

    @cached_property
    def convertors(self) -> "dict[str, FieldConvertor]":
        return dict(self.generate_convertors())

    def generate_convertors(self) -> "Iterator[tuple[str, FieldConvertor]]":
        for parameter in super().extract_parameters():
            cli_parameter = self.create_cli_parameter(parameter)
            dataclass_ = extract_dataclass(resolve_type(cli_parameter))
            if dataclass_ is None:
                convertor: FieldConvertor = ParameterConvertor(cli_parameter)
            else:
                name_prefix = f"{cli_parameter.name}_"
                may_be_absent = cli_parameter.default is not Parameter.empty
                convertor = Convertor(dataclass_, name_prefix, may_be_absent)
            yield parameter.name, convertor

    def create_cli_parameter(self, parameter: Parameter) -> Parameter:
        name = self.name_prefix + parameter.name
        may_be_absent = parameter.default is Parameter.empty and self.may_be_absent
        is_optional = parameter.name in self.default_factory_fields or may_be_absent
        default = None if is_optional else parameter.default
        return parameter.replace(name=name, default=default)

    @property
    def default_factory_fields(self) -> set[str]:
        object_ = typing.cast("type[DataclassInstance]", self.object)
        fields = dataclasses.fields(object_)
        return {
            field_.name
            for field_ in fields
            if field_.default_factory is not dataclasses.MISSING
        }


@dataclass
class ParameterConvertor:
    parameter: Parameter

    def create_value(self, arguments: dict[str, Any]) -> Any:
        return arguments[self.parameter.name]

    def extract_parameters(self) -> Iterator[Parameter]:
        yield self.parameter


FieldConvertor = Convertor[Any] | ParameterConvertor


def extract_dataclass(root: Any) -> "type[DataclassInstance]|None":
    types = (type_ for type_ in extract_types(root) if dataclasses.is_dataclass(type_))
    return typing.cast("type[DataclassInstance]|None", next(types, None))
