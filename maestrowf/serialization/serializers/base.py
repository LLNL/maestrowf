"""Serializer interface for primitive data."""

from abc import ABC, abstractmethod


class PrimitiveSerializer(ABC):
    """Convert primitive data to and from a concrete text or byte format."""

    @abstractmethod
    def dumps(self, data):
        """Serialize primitive data.

        :param data: Primitive value to encode.
        :returns: Encoded representation accepted by a matching ``loads`` call.
        """

    @abstractmethod
    def loads(self, data):
        """Deserialize primitive data.

        :param data: Text or bytes produced by a matching serializer.
        :returns: Decoded primitive value.
        """
