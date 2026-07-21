import pytest

from maestrowf.serialization.errors import (
    PrimitiveTypeError,
    SerializationDecodeError,
)
from maestrowf.serialization.serializers.json import JsonSerializer


def test_json_serializer_round_trips_primitive_data():
    serializer = JsonSerializer()
    data = {"b": [2, None], "a": True}

    encoded = serializer.dumps(data)

    assert encoded.endswith("\n")
    assert serializer.loads(encoded) == data


def test_json_serializer_rejects_non_primitive_data():
    serializer = JsonSerializer()

    with pytest.raises(PrimitiveTypeError):
        serializer.dumps({"items": {1, 2}})


def test_json_serializer_wraps_decode_errors():
    serializer = JsonSerializer()

    with pytest.raises(SerializationDecodeError):
        serializer.loads("{not valid json")
