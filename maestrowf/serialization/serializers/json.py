"""JSON serializer for primitive data."""

import json

from maestrowf.serialization.errors import SerializationDecodeError
from maestrowf.serialization.primitives import validate_primitive
from maestrowf.serialization.serializers.base import PrimitiveSerializer


class JsonSerializer(PrimitiveSerializer):
    """Serialize primitive data as deterministic, human-readable JSON."""

    def __init__(self, indent=2, sort_keys=True):
        self.indent = indent
        self.sort_keys = sort_keys

    def dumps(self, data):
        """Serialize primitive data to a JSON string."""
        validate_primitive(data)
        return (
            json.dumps(
                data,
                indent=self.indent,
                sort_keys=self.sort_keys,
                separators=(",", ": ") if self.indent is not None else None,
            )
            + "\n"
        )

    def loads(self, data):
        """Deserialize primitive data from a JSON string or bytes."""
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        try:
            value = json.loads(data)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SerializationDecodeError(
                "failed to decode JSON checkpoint data"
            ) from exc

        validate_primitive(value)
        return value
