from collections.abc import Callable

from package_utils.cli import instantiate_from_cli_args

from .context import Context
from .models import Config, Options, Secrets


def create_entry_point(
    method: Callable[[], object],
    context: Context[Options, Config, Secrets],
    context_creation_callback: (
        Callable[[Context[Options, Config, Secrets]], None] | None
    ) = None,
) -> Callable[[], None]:
    def entry_point() -> None:
        if context.models.Options is not None:
            context.options = instantiate_from_cli_args(
                context.models.Options,
                documented_object=method,
            )
            if context_creation_callback is not None:
                context_creation_callback(context)
        method()

    return entry_point
