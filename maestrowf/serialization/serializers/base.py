"""Serializer interface for primitive data."""

from abc import ABC, abstractmethod


class PrimitiveSerializer(ABC):
    """Convert primitive data to and from a concrete text or byte format."""

    @abstractmethod
    def dumps(self, data):
        """Serialize primitive data."""

    @abstractmethod
    def loads(self, data):
        """Deserialize primitive data."""
