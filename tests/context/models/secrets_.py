from dataclasses import dataclass


@dataclass
class ApiSecrets:
    id: str
    token: str


@dataclass
class Secrets:
    token: str
    api: ApiSecrets
