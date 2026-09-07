import dataclasses
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import cached_property
from inspect import Parameter, signature
from typing import Any, Generic, TypeVar

import typer

from package_utils.annotations import dataclass_of

T = TypeVar("T")


@dataclass
class Convertor(Generic[T]):
    object: Callable[..., T]
    name_prefix: str = ""
    may_be_absent: bool = False

    def create_value(self, arguments: dict[str, Any]) -> T:
        kwargs = {
            name: convertor.create_value(arguments)
            for name, convertor in self.convertors.items()
            if convertor.is_present(arguments)
        }
        return self.object(**kwargs)

    def is_present(self, arguments: dict[str, Any]) -> bool:
        return not self.may_be_absent or any(
            arguments[parameter.name] is not None
            for parameter in self.flatten_parameters()
        )

    def flatten_parameters(self) -> Iterator[Parameter]:
        for convertor in self.convertors.values():
            yield from convertor.flatten_parameters()

    @property
    def parameter_documentation(self) -> str | None:
        dataclasses_ = [
            dataclass_
            for parameter in self.parameters
            if (dataclass_ := dataclass_of(parameter.annotation))
        ]
        return dataclasses_[0].__doc__ if len(dataclasses_) == 1 else None

    @cached_property
    def convertors(self) -> "dict[str, ParameterConvertor]":
        return {
            parameter.name: self.create_convertor(parameter)
            for parameter in self.parameters
        }

    def create_convertor(self, parameter: Parameter) -> "ParameterConvertor":
        cli_parameter = self.create_cli_parameter(parameter)
        is_sole_parameter = len(self.parameters) == 1
        name_prefix = (
            self.name_prefix if is_sole_parameter else f"{cli_parameter.name}_"
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

    @cached_property
    def parameters(self) -> list[Parameter]:
        signature_ = signature(self.object, eval_str=True, locals={"typer": typer})
        return list(signature_.parameters.values())


@dataclass
class ArgumentConvertor:
    parameter: Parameter

    def create_value(self, arguments: dict[str, Any]) -> Any:
        return arguments[self.parameter.name]

    def is_present(self, arguments: dict[str, Any]) -> bool:
        return arguments[self.parameter.name] is not None

    def flatten_parameters(self) -> Iterator[Parameter]:
        yield self.parameter


ParameterConvertor = Convertor[Any] | ArgumentConvertor
