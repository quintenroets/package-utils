from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Annotated

if TYPE_CHECKING:
    import typer  # pragma: nocover

# defined here instead of imported: pulling them from a module that imports typer
# eagerly would load the package this model exists to keep out
action_help = "Anticipation"
message_help = "Reverberation"


@dataclass
class DeferredOptions:
    """
    Declare typer markers without importing typer at runtime.

    Only a model written this way lets a bare invocation skip the import entirely:
    an eager `import typer` at the top of the model loads it before the entry point
    ever gets to decide.
    """

    action: Annotated[str, typer.Argument(help=action_help)] = "show"
    debug: bool = False
    message: Annotated[str, typer.Option(help=message_help)] = "Hello World!"
    messages: list[str] = field(default_factory=list)
