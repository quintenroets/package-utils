from dataclasses import dataclass

import pytest
from package_dev_utils.tests.args import cli_args, no_cli_args
from typer._click.exceptions import MissingParameter

from package_utils.cli import instantiate_from_cli_args
from tests.cli.models.dataclass_model import NestedOptions, NestedOptionsWithoutDefaults


@dataclass
class Options:
    name: str


@dataclass
class OptionsWithDefaultedNesting:
    nested: NestedOptions
    name: str


@dataclass
class OptionsWithoutDefaultedNesting:
    nested: NestedOptionsWithoutDefaults


@no_cli_args
@pytest.mark.parametrize("class_", [Options, OptionsWithoutDefaultedNesting])
def test_required_field_enforced(class_: type) -> None:
    with pytest.raises(MissingParameter):
        instantiate_from_cli_args(class_)


@cli_args("--name", "name")
def test_required_field_after_nested_defaults() -> None:
    options = instantiate_from_cli_args(OptionsWithDefaultedNesting)
    assert options == OptionsWithDefaultedNesting(NestedOptions(), "name")


@cli_args("--nested-use-nesting")
def test_required_nested_field_supplied() -> None:
    options = instantiate_from_cli_args(OptionsWithoutDefaultedNesting)
    assert options.nested == NestedOptionsWithoutDefaults(use_nesting=True)
