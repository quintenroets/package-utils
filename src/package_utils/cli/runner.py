import inspect
import sys
import types
import typing
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, Generic, Optional, TypeVar

import typer
from plib import Path

T = TypeVar("T")


@dataclass
class CliRunner(Generic[T]):
    method: Callable[..., T]

    @classmethod
    def run_with_cli_args(cls, method: Callable[..., T]) -> Any:
        return CliRunner(method).run()

    def __post_init__(self) -> None:
        self.signature = inspect.signature(self.method)
        self.annotations = typing.get_type_hints(self.method)

    def run(self) -> T:
        self.method.__signature__ = self.create_signature_for_cli_entry()  # type: ignore
        app = typer.Typer(add_completion=False)
        create_command = app.command()
        create_command(self.method)
        result_or_exit_code = app(standalone_mode=False)
        if isinstance(result_or_exit_code, int):
            sys.exit(result_or_exit_code)
        result = typing.cast(T, result_or_exit_code)
        return result

    def create_signature_for_cli_entry(self) -> inspect.Signature:
        parameters_iterator = self.create_parameters_for_cli_entry()
        parameters = list(parameters_iterator)
        return self.signature.replace(parameters=parameters)

    def create_parameters_for_cli_entry(self) -> Iterator[inspect.Parameter]:
        parameters = self.signature.parameters.values()
        for parameter in parameters:
            annotation = self.create_cli_entry_annotation(parameter)
            if isinstance(parameter.default, Enum):
                parameter = parameter.replace(default=parameter.default.value)
            yield parameter.replace(annotation=annotation)

    def create_cli_entry_annotation(self, parameter: inspect.Parameter) -> object:
        annotation = self.annotations[parameter.name]
        path_class = self.extract_path_class(annotation)
        if path_class is not None:
            # monkey patch path convertor
            typer.main.param_path_convertor = path_class
        else:
            annotation = self.adapt_optional_syntax(annotation)
        is_argument = self.is_argument(parameter.annotation)
        Option = typer.Argument if is_argument else typer.Option
        return Annotated[annotation, Option(path_type=path_class)]

    @classmethod
    def adapt_optional_syntax(cls, annotation: object) -> object | None:
        annotations = cls.extract_annotations(annotation)
        if any(sub_annotation is types.NoneType for sub_annotation in annotations):
            optional_annotation = next(
                sub_annotation
                for sub_annotation in annotations
                if sub_annotation is not types.NoneType
            )
            annotation = Optional[optional_annotation]  # noqa: UP007
        return annotation

    @classmethod
    def extract_path_class(cls, annotation: object) -> object | None:
        annotations = cls.extract_annotations(annotation)
        path_annotation = None
        for sub_annotation in annotations:
            if issubclass(sub_annotation, Path):
                path_annotation = sub_annotation
        return path_annotation

    @classmethod
    def extract_annotations(cls, annotation: object) -> tuple[type, ...]:
        is_union = typing.get_origin(annotation) is types.UnionType
        return typing.get_args(annotation) if is_union else (annotation,)

    @classmethod
    def is_argument(cls, annotation: object) -> bool:
        return (
            "typer.Argument(" in annotation
            if isinstance(annotation, str)
            else any(
                isinstance(info, typer.models.ArgumentInfo)
                for info in typing.get_args(annotation)
            )
        )
