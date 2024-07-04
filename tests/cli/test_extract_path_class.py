import inspect
import pathlib
from typing import Optional

import pytest
from package_utils.cli.convertors.parameter import CliParameter
from superpathlib import Path


def extract_path_class(annotation: object) -> type[pathlib.Path] | None:
    parameter = inspect.Parameter("parameter", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    return CliParameter(parameter, annotation).extract_path_class()


@pytest.mark.parametrize(
    ("annotation", "path_class"),
    [
        (Path, Path),
        (pathlib.Path, pathlib.Path),
        (Path | None, Path),
        (Optional[Path], Path),  # noqa: UP007
        (None, None),
        (str, None),
    ],
)
def test_extract_path_class(annotation: object, path_class: type[pathlib.Path]) -> None:
    assert extract_path_class(annotation) == path_class
