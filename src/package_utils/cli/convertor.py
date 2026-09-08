import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from inspect import Parameter
from typing import Any, Generic, TypeVar

from package_utils.annotations import dataclass_of

from .declarations import declared_parameters

T = TypeVar("T")


@dataclass
class Convertor(Generic[T]):
    object: Callable[..., T]
    name_prefix: str = ""
    may_be_absent: bool = False
    documentation_override: str | None = None

    def create_value(self, arguments: dict[str, Any]) -> T:
        kwargs = {
            name: convertor.create_value(arguments)
            for name, convertor in self.convertors.items()
            if convertor.is_present(arguments)
        }
        return self.object(**kwargs)

    def is_present(self, arguments: dict[str, Any]) -> bool:
        return not self.may_be_absent or any(
            arguments[parameter.name] is not None for parameter in self.parameters
        )

    @cached_property
    def parameters(self) -> list[Parameter]:
        return [
            parameter
            for convertor in self.convertors.values()
            for parameter in convertor.parameters
        ]

    @property
    def documentation(self) -> str | None:
        nested = [
            convertor
            for convertor in self.convertors.values()
            if isinstance(convertor, Convertor)
        ]
        only_documentation = nested[0].documentation if len(nested) == 1 else None
        return self.documentation_override or self.object.__doc__ or only_documentation

    @cached_property
    def convertors(self) -> "dict[str, ParameterConvertor]":
        parameters = declared_parameters(self.object)
        is_only_parameter = len(parameters) == 1
        return {
            parameter.name: self.create_convertor(
                parameter, is_only_parameter=is_only_parameter
            )
            for parameter in parameters
        }

    def create_convertor(
        self, parameter: Parameter, *, is_only_parameter: bool
    ) -> "ParameterConvertor":
        cli_parameter = self.create_cli_parameter(parameter)
        name_prefix = (
            self.name_prefix if is_only_parameter else f"{cli_parameter.name}_"
        )
        may_be_absent = cli_parameter.default is not Parameter.empty
        return (
            Convertor(dataclass_, name_prefix, may_be_absent)
            if (dataclass_ := dataclass_of(parameter.annotation))
            else ArgumentConvertor(cli_parameter)
        )

    def create_cli_parameter(self, parameter: Parameter) -> Parameter:
        name = self.name_prefix + parameter.name
        may_be_absent = parameter.default is Parameter.empty and self.may_be_absent
        is_optional = parameter.name in self.default_factory_fields or may_be_absent
        default = None if is_optional else parameter.default
        return parameter.replace(name=name, default=default)

    @cached_property
    def default_factory_fields(self) -> set[str]:
        fields = (
            dataclasses.fields(self.object)
            if dataclasses.is_dataclass(self.object)
            else ()
        )
        return {
            field_.name
            for field_ in fields
            if field_.default_factory is not dataclasses.MISSING
        }


@dataclass
class ArgumentConvertor:
    parameter: Parameter

    def create_value(self, arguments: dict[str, Any]) -> Any:
        return arguments[self.parameter.name]

    def is_present(self, arguments: dict[str, Any]) -> bool:
        return arguments[self.parameter.name] is not None

    @property
    def parameters(self) -> list[Parameter]:
        return [self.parameter]


ParameterConvertor = Convertor[Any] | ArgumentConvertor
