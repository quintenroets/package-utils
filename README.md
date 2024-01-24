# Package Utils
[![PyPI version](https://badge.fury.io/py/package-utils.svg)](https://badge.fury.io/py/package-utils)
![Python version](https://img.shields.io/badge/python-3.10+-brightgreen)
![Operating system](https://img.shields.io/badge/os-linux%20%7c%20macOS%20%7c%20windows-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

## Usage

```python
from dataclasses import dataclass, field
from pathlib import Path

from package_utils.cli.entry_point import create_entry_point


@dataclass
class Options:
    debug: bool = False
    output_path: Path = field(default_factory=Path.cwd)


def main(options: Options):
    ...


entry_point = create_entry_point(main)


if __name__ == "__main__":
    entry_point()
```
see examples in [tests](https://github.com/quintenroets/package-utils/tree/main/tests) and [python-package-template](https://github.com/quintenroets/python-package-template/blob/main/src/python_package_template/cli/entry_point.py)

## Installation
```shell
pip install package-utils
```
