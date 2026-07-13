"""Generic checkpoint envelope helpers."""

import datetime
import platform
from dataclasses import dataclass

from maestrowf import __version__ as MAESTRO_VERSION
from maestrowf.serialization.errors import EnvelopeError
from maestrowf.serialization.primitives import to_primitive, validate_primitive


CHECKPOINT_FORMAT = "maestrowf.checkpoint"


@dataclass(frozen=True)
class EnvelopeInfo:
    """Minimal routing metadata extracted from a checkpoint envelope."""

    format_name: str
    target: str
    schema_version: int


def make_envelope(target, schema_version, payload, created_by=None):
    """Create and validate a generic checkpoint envelope."""
    envelope = {
        "format": CHECKPOINT_FORMAT,
        "target": _validate_target(target),
        "schema_version": _validate_schema_version(schema_version),
        "created_by": _created_by(created_by),
        "payload": to_primitive(payload),
    }
    validate_envelope(envelope)
    return envelope


def inspect_envelope(envelope):
    """Return routing metadata without validating target payload internals."""
    _require_mapping(envelope, "envelope")
    format_name = envelope.get("format")
    target = envelope.get("target")
    schema_version = envelope.get("schema_version")

    if format_name != CHECKPOINT_FORMAT:
        raise EnvelopeError("unsupported checkpoint format {!r}".format(format_name))

    return EnvelopeInfo(
        format_name=format_name,
        target=_validate_target(target),
        schema_version=_validate_schema_version(schema_version),
    )


def validate_envelope(envelope):
    """Validate the generic envelope structure and primitive payload data."""
    _require_mapping(envelope, "envelope")
    missing = [
        key
        for key in ("format", "target", "schema_version", "created_by", "payload")
        if key not in envelope
    ]
    if missing:
        raise EnvelopeError(
            "checkpoint envelope missing keys: {}".format(", ".join(sorted(missing)))
        )

    inspect_envelope(envelope)
    _require_mapping(envelope["created_by"], "created_by")
    validate_primitive(envelope["created_by"], "$.created_by")
    validate_primitive(envelope["payload"], "$.payload")
    return envelope


def _created_by(created_by):
    if created_by is not None:
        _require_mapping(created_by, "created_by")
        return to_primitive(created_by)

    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "maestrowf_version": MAESTRO_VERSION,
        "python_version": platform.python_version(),
        "created_at": now.isoformat().replace("+00:00", "Z"),
    }


def _validate_target(target):
    if not isinstance(target, str) or not target:
        raise EnvelopeError("checkpoint target must be a non-empty string")
    return target


def _validate_schema_version(schema_version):
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise EnvelopeError("schema_version must be an integer")
    if schema_version < 1:
        raise EnvelopeError("schema_version must be >= 1")
    return schema_version


def _require_mapping(value, name):
    if not isinstance(value, dict):
        raise EnvelopeError("{} must be a dictionary".format(name))
