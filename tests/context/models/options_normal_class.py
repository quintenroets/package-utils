from superpathlib import Path


class Options:
    def __init__(self, *, debug: bool = False, config_path: Path = Path.draft) -> None:
        self.debug = debug
        self.config_path = config_path
