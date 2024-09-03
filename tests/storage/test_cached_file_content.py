import typing
from collections.abc import Callable
from typing import Any, TypeVar
from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies
from hypothesis.strategies import SearchStrategy
from superpathlib import Path

from package_utils import storage
from package_utils.storage import CachedFileContent

T = TypeVar("T")

load_patch_target = "package_utils.storage.cached_file_content.CachedFileContent.load"


def dictionary_strategy() -> SearchStrategy[dict[str, str]]:
    text_strategy = strategies.text()
    return strategies.dictionaries(keys=text_strategy, values=text_strategy)


@given(content=dictionary_strategy())
@settings(max_examples=10)
def test_load_only_once(content: dict[str, str]) -> None:
    with Path.tempfile() as path:
        path.yaml = content
        cached_file_content = CachedFileContent[dict[str, str]](path)
        content = cached_file_content.__get__(None)
        with patch(load_patch_target) as load:
            assert cached_file_content.__get__(None) == content
            assert cached_file_content(None) == content
        load.assert_not_called()


@given(content=dictionary_strategy())
@settings(max_examples=10)
def test_default(content: dict[str, str]) -> None:
    with Path.tempfile() as path:
        cached_file_content = CachedFileContent[dict[str, str]](path, default=content)
        assert cached_file_content.__get__(None) == content


@given(content=dictionary_strategy())
@settings(max_examples=10)
def test_reload_after_file_write(content: dict[str, str]) -> None:
    with Path.tempfile() as path:
        cached_file_content = CachedFileContent[dict[str, str]](path)
        path.yaml = content
        with patch(load_patch_target, return_value=content) as load:
            assert cached_file_content.__get__(None) == content
        load.assert_called_once()


@given(content=dictionary_strategy())
@settings(max_examples=10)
def test_no_reload_after_set(content: dict[str, str]) -> None:
    with Path.tempfile() as path:
        cached_file_content = CachedFileContent[dict[str, str]](path)
        with patch(load_patch_target) as load:
            cached_file_content.__set__(None, content)
            assert cached_file_content.__get__(None) == content
        load.assert_not_called()


properties = (storage.cached_path_property, storage.cached_path_dict_property)


@given(content=dictionary_strategy(), content2=dictionary_strategy())
@settings(max_examples=10, deadline=2000)
@pytest.mark.parametrize("cached_path_property", properties)
def test_decorator(
    cached_path_property: Callable[
        ...,
        Callable[[Callable[[Any], T]], CachedFileContent[T]],
    ],
    content: T,
    content2: T,
) -> None:
    with Path.tempfile() as path:

        class TestModel:
            @property
            @cached_path_property(path)
            def content(self) -> T:
                result = path.yaml
                return typing.cast(T, result)

            @content.fget.setter
            def content(self, content_: T) -> None:
                path.yaml = typing.cast(dict[str, str], content_)

        test_model = TestModel()
        test_model.content = content  # type: ignore[method-assign]
        assert test_model.content == content
        path.yaml = typing.cast(dict[str, str], content2)
        # tests are so quick to mtime needs to be increased manually
        path.mtime += 1
        assert test_model.content == content2
