import dataclasses
import typing
from collections.abc import Iterator
from dataclasses import dataclass, field
from inspect import Parameter
from typing import TYPE_CHECKING, Any, TypeVar

from . import method
from .parameter import extract_types, resolve_type

if TYPE_CHECKING:
    from _typeshed import DataclassInstance  # pragma: nocover


T = TypeVar("T")
MISSING_DEFAULTS = (
    Parameter.empty,
    dataclasses._HAS_DEFAULT_FACTORY,  # type: ignore[attr-defined] # noqa: SLF001
)


@dataclass
class Convertor(method.Convertor[T]):
    object: type[T]
    name_prefix: str = ""
    argument_prefixes: dict[str, str] = field(default_factory=dict)

    def call(self, **kwargs: Any) -> T:
        specified_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        if self.argument_prefixes:
            import dacite  # noqa: PLC0415

            self.unflatten(specified_kwargs)
            config = dacite.Config(strict=True)
            result = dacite.from_dict(self.object, specified_kwargs, config=config)
        else:
            result = self.object(**specified_kwargs)
        return result

    def unflatten(self, items: dict[str, Any]) -> None:
        while flattened_names := items.keys() & self.argument_prefixes.keys():
            for name in flattened_names:
                prefix = self.argument_prefixes[name]
                nested_name = name.removeprefix(prefix + "_")
                items.setdefault(prefix, {})[nested_name] = items.pop(name)

    def extract_parameters(self) -> Iterator[Parameter]:
        for parameter in super().extract_parameters():
            cli_parameter = self.create_cli_parameter(parameter)
            dataclass_ = extract_dataclass(resolve_type(cli_parameter))
            if dataclass_ is None:
                yield cli_parameter
            else:
                yield from self.generate_recursive_parameters(cli_parameter, dataclass_)

    def generate_recursive_parameters(
        self,
        parameter: Parameter,
        dataclass_: "type[DataclassInstance]",
    ) -> Iterator[Parameter]:
        convertor = Convertor(dataclass_, name_prefix=f"{parameter.name}_")
        for nested_parameter in convertor.extract_parameters():
            self.argument_prefixes[nested_parameter.name] = parameter.name
            yield nested_parameter

    def create_cli_parameter(self, parameter: Parameter) -> Parameter:
        default = None if parameter.default in MISSING_DEFAULTS else parameter.default
        return parameter.replace(
            name=self.name_prefix + parameter.name,
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            default=default,
        )


def extract_dataclass(root: Any) -> "type[DataclassInstance]|None":
    types = (type_ for type_ in extract_types(root) if dataclasses.is_dataclass(type_))
    return typing.cast("type[DataclassInstance]|None", next(types, None))
