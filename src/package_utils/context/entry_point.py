from collections.abc import Callable
from typing import TypeVar

from ..cli import instantiate_from_cli_args
from .context import Context
from .models import Config, Options, Secrets

T = TypeVar("T")


def create_entry_point(
    method: Callable[[], T], context: Context[Options, Config, Secrets]
) -> Callable[[], T]:
    def entry_point() -> T:
        if context.loaders.options.model is not None:
            context.options = instantiate_from_cli_args(
                context.loaders.options.model, documented_object=method
            )
        return method()

    return entry_point
