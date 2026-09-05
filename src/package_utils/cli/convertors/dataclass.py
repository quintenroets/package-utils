import dataclasses
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cached_property
from inspect import Parameter
from typing import TYPE_CHECKING, Any, TypeVar

from package_utils.annotations import dataclass_of

from . import method

if TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover


T = TypeVar("T")


@dataclass
class Convertor(method.Convertor[T]):
    object: type[T]
    name_prefix: str = ""
    may_be_absent: bool = False

    def create_kwargs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            field_name: value
            for field_name, convertor in self.convertors.items()
            if (value := convertor.create_value(arguments)) is not None
        }

    def create_value(self, arguments: dict[str, Any]) -> T | None:
        kwargs = self.create_kwargs(arguments)
        absent = self.may_be_absent and not kwargs
        return None if absent else self.object(**kwargs)

    def extract_parameters(self) -> Iterator[Parameter]:
        for convertor in self.convertors.values():
            yield from convertor.extract_parameters()

    @cached_property
    def convertors(self) -> "dict[str, FieldConvertor]":
        return {
            parameter.name: self.create_convertor(parameter)
            for parameter in super().extract_parameters()
        }

    def create_convertor(self, parameter: Parameter) -> "FieldConvertor":
        cli_parameter = self.create_cli_parameter(parameter)
        name_prefix = f"{cli_parameter.name}_"
        may_be_absent = cli_parameter.default is not Parameter.empty
        return (
            Convertor(dataclass_, name_prefix, may_be_absent)
            if (dataclass_ := dataclass_of(parameter.annotation))
            else ParameterConvertor(cli_parameter)
        )

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
