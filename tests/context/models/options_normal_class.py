from plib import Path


class Options:
    def __init__(self, debug: bool = False, config_path: Path = Path.draft):
        self.debug = debug
        self.config_path = Path.draft
