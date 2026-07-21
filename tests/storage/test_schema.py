from package_utils.storage.schema import base_type_of


def test_base_type_passes_plain_type_through() -> None:
    assert base_type_of(int) is int


def test_base_type_strips_optional() -> None:
    assert base_type_of(int | None) is int


def test_base_type_reduces_generic_alias_to_origin() -> None:
    assert base_type_of(tuple[int, str]) is tuple


def test_base_type_reduces_optional_generic_alias_to_origin() -> None:
    assert base_type_of(tuple[int, str] | None) is tuple
