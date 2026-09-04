from dataclasses import dataclass, field

import pytest
from package_dev_utils.tests.args import cli_args, no_cli_args
from typer._click.exceptions import MissingParameter

from package_utils.cli import instantiate_from_cli_args
from tests.cli.models.dataclass_model import (
    NestedOptions,
    NestedOptionsWithoutDefaults,
    default_parsed_nested_options,
)


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


@dataclass
class OptionsWithRequiredDeepNesting:
    nested: OptionsWithoutDefaultedNesting


@dataclass
class OptionsWithOptionalDeepNesting:
    nested: OptionsWithoutDefaultedNesting | None = None


@dataclass
class NestedOptionsWithDefaultFactory:
    messages: list[str] = field(default_factory=list)


@dataclass
class OptionsWithRequiredFactoryNesting:
    nested: NestedOptionsWithDefaultFactory


@no_cli_args
@pytest.mark.parametrize(
    "class_", [Options, OptionsWithoutDefaultedNesting, OptionsWithRequiredDeepNesting]
)
def test_required_field_enforced(class_: type) -> None:
    with pytest.raises(MissingParameter):
        instantiate_from_cli_args(class_)


@no_cli_args
def test_optional_deep_nesting_not_enforced() -> None:
    options = instantiate_from_cli_args(OptionsWithOptionalDeepNesting)
    assert options.nested is None


@no_cli_args
def test_required_factory_nesting_constructed() -> None:
    options = instantiate_from_cli_args(OptionsWithRequiredFactoryNesting)
    assert options.nested == NestedOptionsWithDefaultFactory()


@cli_args("--name", "name")
def test_required_field_after_nested_defaults() -> None:
    options = instantiate_from_cli_args(OptionsWithDefaultedNesting)
    assert options == OptionsWithDefaultedNesting(default_parsed_nested_options, "name")


@cli_args("--nested-use-nesting")
def test_required_nested_field_supplied() -> None:
    options = instantiate_from_cli_args(OptionsWithoutDefaultedNesting)
    assert options.nested == NestedOptionsWithoutDefaults(use_nesting=True)
