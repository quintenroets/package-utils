import os
import shlex
import subprocess


def load_secret(name: str) -> str:
    environment_name = name.upper().replace(" ", "_")
    value = os.environ.get(environment_name)
    if not value and (askpass := os.environ.get("SECRET_ASKPASS")):
        command = [*shlex.split(askpass), name]
        value = subprocess.check_output(command).decode().strip()  # noqa: S603
    if not value:
        raise SecretNotFoundError(name, environment_name)
    return value


class SecretNotFoundError(RuntimeError):
    def __init__(self, name: str, environment_name: str) -> None:
        message = (
            f"Secret {name!r} not found (set {environment_name} or SECRET_ASKPASS)"
        )
        super().__init__(message)
