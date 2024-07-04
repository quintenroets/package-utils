from collections.abc import Callable
from typing import TypeVar

from package_utils.cli import instantiate_from_cli_args

from .context import Context
from .models import Config, Options, Secrets

T = TypeVar("T")


def create_entry_point(
    method: Callable[[], T],
    context: Context[Options, Config, Secrets],
    context_creation_callback: (
        Callable[[Context[Options, Config, Secrets]], None] | None
    ) = None,
) -> Callable[[], T]:
    def entry_point() -> T:
        if context.loaders.options.model is not None:
            context.options = instantiate_from_cli_args(
                context.loaders.options.model,
                documented_object=method,
            )
            if context_creation_callback is not None:
                context_creation_callback(context)
        return method()

    return entry_point
