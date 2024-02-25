from dataclasses import dataclass

from superpathlib import Path


@dataclass
class Options:
    debug: bool = False
    config_path: Path = Path.draft
