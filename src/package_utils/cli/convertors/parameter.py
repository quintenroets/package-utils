import collections
import inspect
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer


@dataclass
class CliParameter:
    parameter: inspect.Parameter
    annotation: object

    def convert(self) -> inspect.Parameter:
        Info = typer.Argument if self.is_argument else typer.Option  # noqa: N806
        info = Info(path_type=self.extract_path_class())  # type: ignore[arg-type]
        return self.parameter.replace(annotation=Annotated[self.annotation, info])

    def extract_path_class(self) -> type[Path] | None:
        annotations = self.extract_annotations()
        path_annotation = None
        for sub_annotation in annotations:
            if isinstance(sub_annotation, type) and issubclass(sub_annotation, Path):
                path_annotation = sub_annotation
        return path_annotation

    def extract_annotations(self) -> Iterator[object]:
        annotations = collections.deque([self.annotation])
        while annotations:
            annotation = annotations.popleft()
            sub_annotations = typing.get_args(annotation)
            if sub_annotations:
                annotations.extend(sub_annotations)
            else:
                yield annotation

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
