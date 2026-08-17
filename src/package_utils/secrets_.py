import os
import shlex
import subprocess
from dataclasses import dataclass


@dataclass
class SecretLoader:
    name: str

    def load(self) -> str:
        env_name = self.name.upper().replace(" ", "_")
        value = os.environ.get(env_name)
        if not value and (askpass := os.environ.get("SECRET_ASKPASS")):
            command = [*shlex.split(askpass), self.name]
            value = subprocess.check_output(command).decode().strip()  # noqa: S603
        if not value:
            message = (
                f"Secret {self.name!r} not found (set {env_name} or SECRET_ASKPASS)"
            )
            raise RuntimeError(message)
        return value
