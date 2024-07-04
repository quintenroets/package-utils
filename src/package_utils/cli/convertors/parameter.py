import collections
import inspect
import types
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Optional

import typer

OptionalPathClass = type[Path] | None


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
        self.convert_optional_syntax()
        OptionInfo = typer.Argument if self.is_argument else typer.Option  # noqa: N806
        option_info = OptionInfo(path_type=path_class)  # type: ignore[operator]
        return Annotated[self.annotation, option_info]

    @classmethod
    def monkey_patch_path_convertor(cls, path_class: type[Path]) -> None:
        def convert(value: str | None = None) -> Path | None:
            return None if value is None else path_class(value)

        typer.main.param_path_convertor = convert

    def convert_optional_syntax(self) -> None:
        annotations = self.extract_optional_annotations()
        annotation = next(annotations, None)
        if annotation is not None:
            self.annotation = Optional[annotation]  # noqa: UP007

    def extract_optional_annotations(self) -> Iterator[object]:
        annotations = typing.get_args(self.annotation)
        if types.NoneType in annotations:
            for annotation in annotations:
                if annotation != types.NoneType:
                    yield annotation

    def extract_path_class(self) -> type[Path] | None:
        annotations = self.extract_annotations()
        path_annotation = None
        for sub_annotation in annotations:
            if sub_annotation is not None and issubclass(sub_annotation, Path):
                path_annotation = sub_annotation
        return path_annotation

    def extract_annotations(self) -> Iterator[type]:
        annotations = collections.deque([self.annotation])
        while annotations:
            annotation = annotations.popleft()
            sub_annotations = typing.get_args(annotation)
            if sub_annotations:
                annotations.extend(sub_annotations)
            else:
                yield typing.cast(type, annotation)

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
