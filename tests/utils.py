import sys

import pytest


def forbid_imports(
    monkeypatch: pytest.MonkeyPatch, *names: str, from_module: str
) -> None:
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)
    for module in list(sys.modules):
        if module == from_module or module.startswith(f"{from_module}."):
            monkeypatch.delitem(sys.modules, module)
