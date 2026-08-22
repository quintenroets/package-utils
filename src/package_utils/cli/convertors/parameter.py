import collections
import copy
import inspect
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.models import ParameterInfo


@dataclass
class CliParameter:
    parameter: inspect.Parameter
    annotation: Any

    def convert(self) -> inspect.Parameter:
        infos = (info for info in self.metadata if isinstance(info, ParameterInfo))
        info = copy.copy(next(infos, typer.Option()))
        path_classes = (type_ for type_ in self.extract_types() if is_path_class(type_))
        info.path_type = typing.cast("type[str] | None", next(path_classes, None))
        return self.parameter.replace(annotation=Annotated[self.type_, info])

    def extract_types(self) -> Iterator[object]:
        types = collections.deque([self.type_])
        while types:
            type_ = types.popleft()
            sub_types = typing.get_args(type_)
            if sub_types:
                types.extend(sub_types)
            else:
                yield type_

    @property
    def type_(self) -> Any:
        type_ = self.annotation.__origin__ if self.metadata else self.annotation
        return type_ | None if self.parameter.default is None else type_

    @property
    def metadata(self) -> tuple[Any, ...]:
        return getattr(self.annotation, "__metadata__", ())


def is_path_class(type_: object) -> bool:
    return isinstance(type_, type) and issubclass(type_, Path)
