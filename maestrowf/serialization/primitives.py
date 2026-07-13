"""Helpers for portable primitive serialization data."""

import datetime
import enum
import json
import math
from collections.abc import Mapping
from pathlib import Path

from maestrowf.serialization.errors import PrimitiveTypeError


PRIMITIVE_SCALARS = (str, int, float, bool, type(None))


def validate_primitive(value, path="$"):
    """
    Validate that a value contains only portable primitive data.

    Portable primitives are dictionaries with string keys, lists, strings,
    finite numbers, booleans, and nulls.
    """
    if value is None or isinstance(value, (str, bool)):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise PrimitiveTypeError(
                "{} contains non-finite float {!r}".format(path, value)
            )
        return value

    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_primitive(item, "{}[{}]".format(path, index))
        return value

    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PrimitiveTypeError(
                    "{} contains non-string key {!r}".format(path, key)
                )
            validate_primitive(item, "{}.{}".format(path, key))
        return value

    raise PrimitiveTypeError(
        "{} contains unsupported type {}".format(path, type(value).__name__)
    )


def is_primitive(value):
    """Return True if value contains only portable primitive data."""
    try:
        validate_primitive(value)
    except PrimitiveTypeError:
        return False
    return True


def to_primitive(value):
    """
    Convert common simple values to portable primitive data.

    This helper is intentionally conservative. It handles basic containers,
    enums, datetimes, dates, paths, and sets. Domain-specific objects should be
    converted by target projectors instead.
    """
    if value is None or isinstance(value, (str, bool, int)):
        return value

    if isinstance(value, float):
        validate_primitive(value)
        return value

    if isinstance(value, enum.Enum):
        return value.name

    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise PrimitiveTypeError(
                    "mapping contains non-string key {!r}".format(key)
                )
            result[key] = to_primitive(item)
        return result

    if isinstance(value, (list, tuple)):
        return [to_primitive(item) for item in value]

    if isinstance(value, (set, frozenset)):
        items = [to_primitive(item) for item in value]
        for item in items:
            validate_primitive(item)
        return sorted(items, key=_stable_sort_key)

    raise PrimitiveTypeError("unsupported type {}".format(type(value).__name__))


def _stable_sort_key(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
