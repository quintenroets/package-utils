import inspect
import sys
import types
import typing
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated, Any, Generic, TypeVar

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
            yield parameter.replace(annotation=annotation)

    def create_cli_entry_annotation(self, parameter: inspect.Parameter) -> object:
        annotation = self.annotations[parameter.name]
        path_class = self.extract_path_class(annotation)
        if path_class is not None:
            # monkey patch path convertor
            typer.main.param_path_convertor = path_class
            annotation = Annotated[annotation, typer.Option(path_type=path_class)]
        return annotation

    @classmethod
    def extract_path_class(cls, annotation: object) -> object | None:
        is_union = typing.get_origin(annotation) is types.UnionType
        type_annotations = typing.get_args(annotation) if is_union else (annotation,)
        path_annotation = None
        for sub_annotation in type_annotations:
            if issubclass(sub_annotation, Path):
                path_annotation = sub_annotation
        return path_annotation
