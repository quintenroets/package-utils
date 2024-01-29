from dataclasses import dataclass

from plib import Path


@dataclass
class Options:
    debug: bool = False
    config_path: Path = Path.draft
