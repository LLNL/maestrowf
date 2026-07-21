import pytest

from maestrowf.serialization.envelope import make_envelope
from maestrowf.serialization.errors import FutureVersionError, MigrationError
from maestrowf.serialization.migrations import MigrationRegistry


def test_upgrade_returns_current_version_without_migration():
    registry = MigrationRegistry()
    envelope = make_envelope("execution_graph_checkpoint", 1, {"value": "old"})

    upgraded = registry.upgrade(envelope, current_version=1)

    assert upgraded == envelope
    assert upgraded is not envelope


def test_upgrade_applies_registered_migrations_in_order():
    registry = MigrationRegistry()

    @registry.register("execution_graph_checkpoint", 1)
    def v1_to_v2(envelope):
        status_by_step = {}
        for step in envelope["payload"]["steps"]:
            status_by_step[step["name"]] = step.pop("status")
        envelope["payload"]["run_state"] = {"status_by_step": status_by_step}
        envelope["schema_version"] = 2
        return envelope

    @registry.register("execution_graph_checkpoint", 2)
    def v2_to_v3(envelope):
        envelope["payload"]["definition"] = {
            "steps": envelope["payload"].pop("steps"),
        }
        envelope["schema_version"] = 3
        return envelope

    upgraded = registry.upgrade(
        make_envelope(
            "execution_graph_checkpoint",
            1,
            {"steps": [{"name": "hello", "status": "DONE"}]},
        ),
        current_version=3,
    )

    assert upgraded["schema_version"] == 3
    assert upgraded["payload"] == {
        "definition": {"steps": [{"name": "hello"}]},
        "run_state": {"status_by_step": {"hello": "DONE"}},
    }


def test_upgrade_rejects_future_version():
    registry = MigrationRegistry()
    envelope = make_envelope("execution_graph_checkpoint", 3, {})

    with pytest.raises(FutureVersionError):
        registry.upgrade(envelope, current_version=2)


def test_upgrade_rejects_missing_migration():
    registry = MigrationRegistry()
    envelope = make_envelope("execution_graph_checkpoint", 1, {})

    with pytest.raises(MigrationError):
        registry.upgrade(envelope, current_version=2)


def test_upgrade_rejects_migration_that_skips_expected_version():
    registry = MigrationRegistry()

    @registry.register("execution_graph_checkpoint", 1)
    def v1_to_v2(envelope):
        envelope["schema_version"] = 3
        return envelope

    with pytest.raises(MigrationError):
        registry.upgrade(
            make_envelope("execution_graph_checkpoint", 1, {}),
            current_version=2,
        )
