import dataclasses
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

import typer

from . import convertors

T = TypeVar("T")


@dataclass
class Runner(Generic[T]):
    object: Callable[..., T] | type[T]

    def run_with_cli_args(self) -> T:
        is_dataclass = dataclasses.is_dataclass(self.object)
        module = convertors.dataclass if is_dataclass else convertors.method
        cli_entry_method = module.Convertor(self.object).run()
        return self.run_cli_entry_method(cli_entry_method)

    @classmethod
    def run_cli_entry_method(cls, method: Callable[..., T]) -> T:
        app = typer.Typer(add_completion=False)
        create_command = app.command()
        create_command(method)
        return cls.run_app(app)

    @classmethod
    def run_app(cls, app: typer.Typer) -> T:
        result_or_exit_code = app(standalone_mode=False)
        if isinstance(result_or_exit_code, int):
            sys.exit(result_or_exit_code)
        return cast("T", result_or_exit_code)
