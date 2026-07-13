"""File-backed checkpoint repository."""

import os

from filelock import FileLock

from maestrowf.serialization.serializers.json import JsonSerializer
from maestrowf.utils import atomic_write_file


class FileCheckpointRepository:
    """Load and save primitive checkpoints using a lock and atomic replace."""

    def __init__(self, path, serializer=None, lock_path=None):
        self.path = os.fspath(path)
        self.serializer = serializer or JsonSerializer()
        self.lock_path = os.fspath(lock_path or "{}.lock".format(self.path))

    def exists(self):
        """Return True if the checkpoint file exists."""
        return os.path.exists(self.path)

    def save(self, checkpoint):
        """Serialize and atomically save a checkpoint."""
        contents = self.serializer.dumps(checkpoint)
        with FileLock(self.lock_path):
            atomic_write_file(self.path, contents)

    def load(self):
        """Load and deserialize a checkpoint."""
        with FileLock(self.lock_path):
            with open(self.path, "r", encoding="utf-8") as checkpoint_file:
                contents = checkpoint_file.read()
        return self.serializer.loads(contents)
