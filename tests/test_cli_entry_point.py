import pytest
from python_package_template import cli


def test_testing() -> None:
    with pytest.raises(SystemExit) as exception:
        cli.entry_point()
    assert exception.value.code == 0
