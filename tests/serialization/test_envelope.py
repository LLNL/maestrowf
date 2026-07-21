import pytest

from maestrowf import __version__ as MAESTRO_VERSION
from maestrowf.serialization.envelope import (
    DOCUMENT_FORMAT,
    EnvelopeInfo,
    inspect_envelope,
    make_envelope,
    validate_envelope,
)
from maestrowf.serialization.errors import EnvelopeError


def test_make_envelope_adds_generic_document_metadata():
    envelope = make_envelope(
        target="study_workspace_index",
        schema_version=1,
        payload={"workspaces": []},
    )

    assert envelope["format"] == DOCUMENT_FORMAT
    assert envelope["target"] == "study_workspace_index"
    assert envelope["schema_version"] == 1
    assert envelope["payload"] == {"workspaces": []}
    assert envelope["created_by"]["maestrowf_version"] == MAESTRO_VERSION
    assert "python_version" in envelope["created_by"]
    assert "python_executable" in envelope["created_by"]
    assert envelope["created_by"]["created_at"].endswith("Z")


def test_inspect_envelope_returns_routing_metadata():
    envelope = make_envelope(
        target="execution_graph_checkpoint",
        schema_version=2,
        payload={},
    )

    assert inspect_envelope(envelope) == EnvelopeInfo(
        format_name=DOCUMENT_FORMAT,
        target="execution_graph_checkpoint",
        schema_version=2,
    )


def test_validate_envelope_rejects_missing_required_key():
    envelope = make_envelope(
        target="execution_graph_checkpoint",
        schema_version=1,
        payload={},
    )
    del envelope["payload"]

    with pytest.raises(EnvelopeError):
        validate_envelope(envelope)


@pytest.mark.parametrize(
    "schema_version",
    [
        pytest.param(0, id="zero-is-reserved"),
        pytest.param(True, id="bool-is-not-int"),
        pytest.param("1", id="string-is-not-int"),
    ],
)
def test_make_envelope_rejects_invalid_schema_version(schema_version):
    with pytest.raises(EnvelopeError):
        make_envelope(
            target="execution_graph_checkpoint",
            schema_version=schema_version,
            payload={},
        )
