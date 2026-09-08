import sys

import pytest


def forbid_imports(
    monkeypatch: pytest.MonkeyPatch, *names: str, from_module: str
) -> None:
    for name in names:
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.delitem(sys.modules, from_module, raising=False)
