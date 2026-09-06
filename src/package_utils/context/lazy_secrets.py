from __future__ import annotations

import typing
from dataclasses import MISSING, Field, fields
from functools import cached_property, partial
from typing import Any, ClassVar, get_type_hints

from package_utils import secrets_
from package_utils.annotations import dataclass_of

if typing.TYPE_CHECKING:  # pragma: nocover
    from _typeshed import DataclassInstance


def create_lazy_secrets(
    model: type[DataclassInstance], prefix: str = ""
) -> DataclassInstance:
    type_hints = get_type_hints(model)
    properties = {
        field_.name: cached_property(
            partial(resolve, field_, type_hints[field_.name], prefix)
        )
        for field_ in fields(model)
    }
    methods = {"__init__": object.__init__, "__hash__": model.__hash__}
    class_ = type(model.__name__, (LazySecrets, model), properties | methods)
    return typing.cast("DataclassInstance", class_())


class LazySecrets:  # noqa: PLW1641
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]

    def __repr__(self) -> str:
        fields_ = ", ".join(
            f"{field_.name}={represent(self, field_.name)}"
            for field_ in fields(self)
            if field_.repr
        )
        return f"{type(self).__name__}({fields_})"

    def __eq__(self, other: object) -> bool:
        model = type(self).__bases__[-1]
        matches = (
            getattr(self, field_.name) == getattr(other, field_.name)
            for field_ in fields(self)
        )
        return all(matches) if isinstance(other, model) else NotImplemented


def resolve(field_: Field[Any], annotation: Any, prefix: str, _instance: object) -> Any:
    name = f"{prefix}_{field_.name}" if prefix else field_.name
    return (
        load_with_fallback(field_, name)
        if (nested_model := dataclass_of(annotation)) is None
        else create_lazy_secrets(nested_model, name)
    )


def represent(instance: LazySecrets, name: str) -> str:
    value = instance.__dict__.get(name, MISSING)
    return (
        "<unresolved>"
        if value is MISSING
        else repr(value)
        if isinstance(value, LazySecrets)
        else "***"
    )


def load_with_fallback(field_: Field[Any], name: str) -> Any:
    try:
        value = secrets_.load_secret(name)
    except secrets_.SecretNotFoundError:
        factory = field_.default_factory
        fallback = field_.default if factory is MISSING else factory()
        if fallback is MISSING:
            raise
        value = fallback
    return value
