from dataclasses import dataclass

from plib import Path


@dataclass
class Config:
    output_path: Path = None
    secrets_path: Path = None
