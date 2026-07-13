"""Error types raised by Maestro serialization infrastructure."""


class SerializationError(Exception):
    """Base class for serialization infrastructure errors."""


class PrimitiveTypeError(SerializationError, TypeError):
    """Raised when a value cannot be represented as portable primitives."""


class EnvelopeError(SerializationError, ValueError):
    """Raised when a document envelope is missing required structure."""


class SerializationDecodeError(SerializationError, ValueError):
    """Raised when primitive data cannot be decoded from a concrete format."""


class MigrationError(SerializationError, ValueError):
    """Raised when a schema migration path is invalid or unavailable."""


class FutureVersionError(MigrationError):
    """Raised when a document is newer than the supported schema version."""
