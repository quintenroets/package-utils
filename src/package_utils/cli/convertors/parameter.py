import collections
import dataclasses
import inspect
import types
import typing
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Optional

if TYPE_CHECKING:  # pragma: nocover
    from _typeshed import DataclassInstance

OptionalPathClass = type[Path] | None


@dataclass
class CliParameter:
    parameter: inspect.Parameter
    annotation: object
    # the same annotation with its typer marker intact, so `help` and argument
    # versus option survive rebuilding the marker
    declared_annotation: object

    @property
    def default(self) -> Any:
        return self.parameter.default

    @property
    def declared_info(self) -> Any:
        """The `typer.Argument()` or `typer.Option()` the caller wrote, if any."""
        metadata = getattr(self.declared_annotation, "__metadata__", ())
        return next(iter(metadata), None)

    @property
    def help_text(self) -> str | None:
        return getattr(self.declared_info, "help", None)

    def convert(self) -> inspect.Parameter:
        annotation = self.convert_annotation()
        default = self.convert_default()
        return self.parameter.replace(annotation=annotation, default=default)

    def convert_default(self) -> object:
        return self.default.value if isinstance(self.default, Enum) else self.default

    def convert_annotation(self) -> object:
        import typer

        path_class = self.extract_path_class()
        if path_class is not None:
            self.monkey_patch_path_convertor(path_class)
        self.convert_optional_syntax()
        OptionInfo = typer.Argument if self.is_argument else typer.Option  # noqa: N806
        option_info = OptionInfo(path_type=path_class, help=self.help_text)  # type: ignore[arg-type]
        return Annotated[self.annotation, option_info]

    @classmethod
    def monkey_patch_path_convertor(cls, path_class: type[Path]) -> None:
        import typer

        def convert(value: str | None = None) -> Path | None:
            return None if value is None else path_class(value)

        typer.main.param_path_convertor = convert

    def convert_optional_syntax(self) -> None:
        annotations = self.extract_optional_annotations()
        annotation = next(annotations, None)
        if annotation is not None:
            self.annotation = Optional[annotation]  # noqa: UP045

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
        yield from generate_annotations(self.annotation)

    @property
    def is_argument(self) -> bool:
        import typer

        return isinstance(self.declared_info, typer.models.ArgumentInfo)


def resolve_annotations(
    object_: object,
    typer_binding: object,
    *,
    include_extras: bool = False,
) -> dict[str, Any]:
    """
    Resolve declared types with `typer` bound to whatever the caller can afford.

    Annotations carry `typer.Argument()` and `typer.Option()` calls, so a caller that
    defers its own typer import leaves the name unbound where those get evaluated.
    Supplying the binding keeps resolution working either way: the real module where
    the markers themselves are read, a stub where only the types underneath them are.
    """
    return typing.get_type_hints(
        object_,
        localns={"typer": typer_binding},
        include_extras=include_extras,
    )


class TyperMarker:
    """
    Stand in for the `typer.Argument()` and `typer.Option()` calls in annotations.

    Attribute access answers with the class itself, so those calls construct one of
    these instead of reaching typer. Callers that resolve against this stub discard
    the extras anyway, so nothing beyond the call succeeding matters.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Accept whatever the real marker accepts."""

    def __getattr__(self, name: str) -> type["TyperMarker"]:
        return TyperMarker


def extract_dataclass(annotation: object) -> "type[DataclassInstance] | None":
    """Find the dataclass an annotation resolves to, looking through unions."""
    annotations = (
        sub_annotation
        for sub_annotation in generate_annotations(annotation)
        if dataclasses.is_dataclass(sub_annotation)
    )
    return next(annotations, None)


def generate_annotations(annotation: object) -> Iterator[type]:
    annotations = collections.deque([annotation])
    while annotations:
        annotation = annotations.popleft()
        sub_annotations = typing.get_args(annotation)
        if sub_annotations:
            annotations.extend(sub_annotations)
        else:
            yield typing.cast("type", annotation)
