"""Generic Maestro document envelope helpers.

An envelope is the small, target-agnostic wrapper around a primitive payload.
It lets generic infrastructure identify a serialized Maestro document, route it
to the right target-specific migration/builder code, and preserve producer
provenance without understanding the payload schema.

Envelope values are ordinary primitive dictionaries with this shape:

.. code-block:: python

    {
        "format": DOCUMENT_FORMAT,
        "target": "execution_graph_checkpoint",
        "schema_version": 1,
        "created_by": {...},
        "payload": {...},
    }

The ``payload`` belongs to the target-specific layer. The generic envelope
helpers only validate that the wrapper and payload are portable primitive data.
"""

import datetime
import platform
import sys
from dataclasses import dataclass

from maestrowf import __version__ as MAESTRO_VERSION
from maestrowf.serialization.errors import EnvelopeError
from maestrowf.serialization.primitives import to_primitive, validate_primitive


# Magic value for the outer wrapper contract. This says "read me as a Maestro
# versioned document envelope"; it is independent of concrete encodings such as
# JSON, YAML, or database rows and intentionally does not identify the payload
# type. Payload routing is handled by the open string ``target`` field.
DOCUMENT_FORMAT = "maestrowf.document"


@dataclass(frozen=True)
class EnvelopeInfo:
    """Minimal routing metadata extracted from a document envelope.

    This small view is returned by ``inspect_envelope`` for migration dispatch
    and other routing code. Functions that create or validate envelopes return
    the full primitive dictionary because callers still need ``created_by`` and
    ``payload``.

    :ivar format_name: Outer envelope protocol. This must match
        ``DOCUMENT_FORMAT`` and is not the JSON/YAML/database encoding.
    :ivar target: Open string identifier for the payload contract, such as
        ``execution_graph_checkpoint`` or ``study_workspace_index``.
    :ivar schema_version: Version of the target payload schema. This version is
        scoped to ``target``, not to the generic envelope.
    """

    format_name: str
    target: str
    schema_version: int


def make_envelope(target, schema_version, payload):
    """Create and validate a generic Maestro document envelope.

    :param target: Open string identifier owned by target-specific modules,
        not a closed enum in the generic serialization layer. Examples include
        ``execution_graph_checkpoint`` and the future ``study_workspace_index``.
    :param schema_version: Version of the target payload schema. The generic
        envelope shape is stable and is not versioned separately here.
    :param payload: Target-specific data to store under the envelope's
        ``payload`` key. It may be any value accepted by ``to_primitive``.
    :returns: A primitive dictionary ready for JSON/YAML serialization or for a
        repository/database layer to store as structured data.
    :rtype: dict
    :raises EnvelopeError: If the target or schema version is not valid for a
        generic envelope.
    """
    envelope = {
        "format": DOCUMENT_FORMAT,
        "target": _validate_target(target),
        "schema_version": _validate_schema_version(schema_version),
        "created_by": _created_by_metadata(),
        "payload": to_primitive(payload),
    }
    validate_envelope(envelope)
    return envelope


def inspect_envelope(envelope):
    """Return envelope routing metadata without validating payload internals.

    Returns an ``EnvelopeInfo`` rather than the original dictionary because
    routing code should not need or accidentally depend on ``created_by`` or
    target-specific ``payload`` contents.

    :param envelope: Primitive dictionary or dictionary-like value with at
        least ``format``, ``target``, and ``schema_version``. This helper is
        the cheap first pass used by migration registries and loaders to decide
        which target-specific code should handle the document.
    :returns: Minimal routing view containing ``format_name``, ``target``, and
        ``schema_version``.
    :rtype: EnvelopeInfo
    :raises EnvelopeError: If the value is not an envelope dictionary, the
        format is unsupported, or the routing metadata is malformed.
    """
    _require_mapping(envelope, "envelope")
    format_name = envelope.get("format")
    target = envelope.get("target")
    schema_version = envelope.get("schema_version")

    if format_name != DOCUMENT_FORMAT:
        raise EnvelopeError("unsupported document format {!r}".format(format_name))

    return EnvelopeInfo(
        format_name=format_name,
        target=_validate_target(target),
        schema_version=_validate_schema_version(schema_version),
    )


def validate_envelope(envelope):
    """Validate the full generic envelope and return it unchanged.

    This validates the generic wrapper keys, producer provenance, and that
    ``payload`` is portable primitive data. It intentionally does not validate
    the target payload schema; that is owned by the target-specific builder or
    schema module.

    :param envelope: Full primitive dictionary produced by ``make_envelope`` or
        loaded from storage.
    :returns: The same envelope dictionary, unchanged.
    :rtype: dict
    :raises EnvelopeError: If required wrapper keys or routing metadata are
        missing or malformed.
    :raises PrimitiveTypeError: If ``created_by`` or ``payload`` contains data
        that cannot be represented as portable primitives.
    """
    _require_mapping(envelope, "envelope")
    missing = [
        key
        for key in ("format", "target", "schema_version", "created_by", "payload")
        if key not in envelope
    ]
    if missing:
        raise EnvelopeError(
            "document envelope missing keys: {}".format(", ".join(sorted(missing)))
        )

    inspect_envelope(envelope)
    _require_mapping(envelope["created_by"], "created_by")
    validate_primitive(envelope["created_by"], "$.created_by")
    validate_primitive(envelope["payload"], "$.payload")
    return envelope


def _created_by_metadata():
    """Return the value stored in the envelope's ``created_by`` field.

    The field value is a flat producer-metadata dictionary with only the
    baseline provenance PR 1 needs. Optional producer extension metadata is
    intentionally deferred until a concrete target or repository needs it.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    return {
        "maestrowf_version": MAESTRO_VERSION,
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "created_at": now.isoformat().replace("+00:00", "Z"),
    }


def _validate_target(target):
    if not isinstance(target, str) or not target:
        raise EnvelopeError("document target must be a non-empty string")
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
