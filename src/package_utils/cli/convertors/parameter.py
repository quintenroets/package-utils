import inspect
import types
import typing
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any, Optional

import typer
from plib import Path


@dataclass
class CliParameter:
    parameter: inspect.Parameter
    annotation: object

    @property
    def default(self) -> Any:
        return self.parameter.default

    def convert(self) -> inspect.Parameter:
        annotation = self.convert_annotation()
        default = self.convert_default()
        return self.parameter.replace(annotation=annotation, default=default)

    def convert_default(self) -> object:
        return self.default.value if isinstance(self.default, Enum) else self.default

    def convert_annotation(self) -> object:
        path_class = self.extract_path_class()
        if path_class is not None:
            self.monkey_patch_path_convertor(path_class)
        else:
            self.convert_optional_syntax()
        Option = typer.Argument if self.is_argument else typer.Option
        return Annotated[self.annotation, Option(path_type=path_class)]

    @classmethod
    def monkey_patch_path_convertor(cls, path_class: type[Path]) -> None:
        typer.main.param_path_convertor = path_class

    def convert_optional_syntax(self) -> None:
        annotations = self.extract_annotations()
        if any(sub_annotation is types.NoneType for sub_annotation in annotations):
            optional_annotation = next(
                sub_annotation
                for sub_annotation in annotations
                if sub_annotation is not types.NoneType
            )
            self.annotation = Optional[optional_annotation]  # noqa: UP007

    def extract_path_class(self) -> type[Path] | None:
        annotations = self.extract_annotations()
        path_annotation = None
        for sub_annotation in annotations:
            if issubclass(sub_annotation, Path):
                path_annotation = sub_annotation
        return path_annotation

    def extract_annotations(self) -> tuple[type, ...]:
        is_union = typing.get_origin(self.annotation) is types.UnionType
        return typing.get_args(self.annotation) if is_union else (self.annotation,)

    @property
    def is_argument(self) -> bool:
        annotation = self.parameter.annotation
        return (
            "typer.Argument(" in annotation
            if isinstance(annotation, str)
            else any(
                isinstance(info, typer.models.ArgumentInfo)
                for info in typing.get_args(annotation)
            )
        )
