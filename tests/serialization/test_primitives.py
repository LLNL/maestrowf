import datetime
import enum
from pathlib import Path

import pytest

from maestrowf.serialization.errors import PrimitiveTypeError
from maestrowf.serialization.primitives import (
    is_primitive,
    to_primitive,
    validate_primitive,
)


class ExampleState(enum.Enum):
    READY = "ready"


def test_validate_primitive_accepts_portable_tree():
    data = {
        "name": "step",
        "attempt": 1,
        "elapsed": 1.5,
        "done": False,
        "children": ["a", None],
    }

    assert validate_primitive(data) is data
    assert is_primitive(data)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_validate_primitive_rejects_non_finite_float(value):
    with pytest.raises(PrimitiveTypeError):
        validate_primitive({"value": value})


def test_validate_primitive_rejects_non_string_mapping_keys():
    with pytest.raises(PrimitiveTypeError):
        validate_primitive({1: "one"})


def test_to_primitive_converts_common_simple_values():
    value = {
        "state": ExampleState.READY,
        "created": datetime.datetime(2026, 7, 7, 1, 2, 3),
        "path": Path("workspace/step"),
        "tags": {"b", "a"},
        "items": ("x", "y"),
    }

    assert to_primitive(value) == {
        "state": "READY",
        "created": "2026-07-07T01:02:03",
        "path": "workspace/step",
        "tags": ["a", "b"],
        "items": ["x", "y"],
    }
