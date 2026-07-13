"""JSON serializer for primitive data."""

import json

from maestrowf.serialization.errors import SerializationDecodeError
from maestrowf.serialization.primitives import validate_primitive
from maestrowf.serialization.serializers.base import PrimitiveSerializer


class JsonSerializer(PrimitiveSerializer):
    """Serialize primitive data as deterministic, human-readable JSON."""

    def __init__(self, indent=2, sort_keys=True):
        """Create a JSON primitive serializer.

        :param indent: Indentation passed to ``json.dumps``. Use ``None`` for
            compact JSON.
        :param sort_keys: Whether dictionary keys should be sorted for stable
            output.
        """
        self.indent = indent
        self.sort_keys = sort_keys

    def dumps(self, data):
        """Serialize primitive data to a JSON string.

        :param data: Primitive value to encode.
        :returns: JSON text ending with a newline.
        :rtype: str
        :raises PrimitiveTypeError: If ``data`` contains unsupported values.
        """
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
        """Deserialize primitive data from a JSON string or bytes.

        :param data: JSON text as ``str`` or UTF-8 ``bytes``.
        :returns: Decoded primitive value.
        :raises SerializationDecodeError: If JSON decoding fails.
        :raises PrimitiveTypeError: If the decoded data contains unsupported
            primitive values.
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        try:
            value = json.loads(data)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SerializationDecodeError(
                "failed to decode JSON primitive data"
            ) from exc

        validate_primitive(value)
        return value
