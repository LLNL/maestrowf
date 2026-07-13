import pytest

from maestrowf.serialization.envelope import make_envelope
from maestrowf.serialization.repositories.file import FileCheckpointRepository
from maestrowf.serialization.serializers.json import JsonSerializer


def test_file_repository_saves_and_loads_checkpoint(tmp_path):
    path = tmp_path / "study.state.json"
    repository = FileCheckpointRepository(path)
    checkpoint = make_envelope(
        target="execution_graph_checkpoint",
        schema_version=1,
        payload={"steps": ["hello"]},
    )

    repository.save(checkpoint)

    assert repository.exists()
    assert repository.load() == checkpoint


def test_file_repository_does_not_replace_last_good_checkpoint_on_error(tmp_path):
    path = tmp_path / "study.state.json"
    repository = FileCheckpointRepository(path)
    last_good = make_envelope(
        target="execution_graph_checkpoint",
        schema_version=1,
        payload={"version": "good"},
    )
    repository.save(last_good)

    failing_repository = FileCheckpointRepository(
        path,
        serializer=FailingSerializer(),
    )

    with pytest.raises(RuntimeError):
        failing_repository.save({"version": "bad"})

    assert repository.load() == last_good


class FailingSerializer(JsonSerializer):
    def dumps(self, data):
        raise RuntimeError("cannot serialize")
