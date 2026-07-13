import pytest

from maestrowf.serialization.envelope import (
    CHECKPOINT_FORMAT,
    EnvelopeInfo,
    inspect_envelope,
    make_envelope,
    validate_envelope,
)
from maestrowf.serialization.errors import EnvelopeError


def test_make_envelope_adds_generic_checkpoint_metadata():
    envelope = make_envelope(
        target="execution_graph",
        schema_version=1,
        payload={"steps": []},
        created_by={"tester": "unit"},
    )

    assert envelope == {
        "format": CHECKPOINT_FORMAT,
        "target": "execution_graph",
        "schema_version": 1,
        "created_by": {"tester": "unit"},
        "payload": {"steps": []},
    }


def test_inspect_envelope_returns_routing_metadata():
    envelope = make_envelope(
        target="execution_graph",
        schema_version=2,
        payload={},
        created_by={},
    )

    assert inspect_envelope(envelope) == EnvelopeInfo(
        format_name=CHECKPOINT_FORMAT,
        target="execution_graph",
        schema_version=2,
    )


def test_validate_envelope_rejects_missing_required_key():
    envelope = make_envelope(
        target="execution_graph",
        schema_version=1,
        payload={},
        created_by={},
    )
    del envelope["payload"]

    with pytest.raises(EnvelopeError):
        validate_envelope(envelope)


@pytest.mark.parametrize("schema_version", [0, True, "1"])
def test_make_envelope_rejects_invalid_schema_version(schema_version):
    with pytest.raises(EnvelopeError):
        make_envelope(
            target="execution_graph",
            schema_version=schema_version,
            payload={},
        )
