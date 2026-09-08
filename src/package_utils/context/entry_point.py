from collections.abc import Callable

from package_utils.cli.entry_point import invoke_from_cli_args

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
            context.options = invoke_from_cli_args(
                context.models.Options, method.__doc__
            )
            if context_creation_callback is not None:
                context_creation_callback(context)
        method()

    return entry_point
