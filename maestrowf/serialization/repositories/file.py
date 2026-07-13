"""File-backed checkpoint repository."""

import os

from filelock import FileLock

from maestrowf.serialization.serializers.json import JsonSerializer
from maestrowf.utils import atomic_write_file


class FileCheckpointRepository:
    """Load and save primitive checkpoints using a lock and atomic replace."""

    def __init__(self, path, serializer=None, lock_path=None):
        """Create a file-backed checkpoint repository.

        :param path: Checkpoint file path.
        :param serializer: Primitive serializer used for file contents. When
            omitted, ``JsonSerializer`` is used.
        :param lock_path: Optional lock file path. When omitted, ``.lock`` is
            appended to ``path``.
        """
        self.path = os.fspath(path)
        self.serializer = serializer or JsonSerializer()
        self.lock_path = os.fspath(lock_path or "{}.lock".format(self.path))

    def exists(self):
        """Return whether the checkpoint file exists.

        :returns: ``True`` if the checkpoint file exists.
        :rtype: bool
        """
        return os.path.exists(self.path)

    def save(self, checkpoint):
        """Serialize and atomically save a checkpoint.

        :param checkpoint: Primitive checkpoint envelope to persist.
        """
        contents = self.serializer.dumps(checkpoint)
        with FileLock(self.lock_path):
            atomic_write_file(self.path, contents)

    def load(self):
        """Load and deserialize a checkpoint.

        :returns: Primitive checkpoint envelope loaded from disk.
        :rtype: dict
        """
        with FileLock(self.lock_path):
            with open(self.path, "r", encoding="utf-8") as checkpoint_file:
                contents = checkpoint_file.read()
        return self.serializer.loads(contents)
