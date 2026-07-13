"""Schema migration registry for primitive checkpoint envelopes."""

import copy

from maestrowf.serialization.envelope import (
    inspect_envelope,
    validate_envelope,
)
from maestrowf.serialization.errors import FutureVersionError, MigrationError


class MigrationRegistry:
    """Register and apply target-specific checkpoint schema migrations."""

    def __init__(self):
        self._migrations = {}

    def register(self, target, from_version, to_version=None, func=None):
        """
        Register a migration function.

        If called without ``func``, this returns a decorator. Migration
        functions receive a primitive envelope and must return a primitive
        envelope for the next schema version.
        """
        if to_version is None:
            to_version = from_version + 1

        self._validate_step(target, from_version, to_version)

        def decorator(migration_func):
            key = (target, from_version, to_version)
            if key in self._migrations:
                raise MigrationError("migration already registered for {}".format(key))
            self._migrations[key] = migration_func
            return migration_func

        if func is not None:
            return decorator(func)
        return decorator

    def upgrade(self, envelope, current_version):
        """Upgrade an envelope to the current schema version for its target."""
        envelope = copy.deepcopy(validate_envelope(envelope))
        info = inspect_envelope(envelope)

        if info.schema_version > current_version:
            raise FutureVersionError(
                "{} schema version {} is newer than supported version {}".format(
                    info.target, info.schema_version, current_version
                )
            )

        while info.schema_version < current_version:
            next_version = info.schema_version + 1
            key = (info.target, info.schema_version, next_version)
            migration = self._migrations.get(key)
            if migration is None:
                raise MigrationError(
                    "no migration registered for {} v{} to v{}".format(
                        info.target, info.schema_version, next_version
                    )
                )

            envelope = validate_envelope(migration(copy.deepcopy(envelope)))
            migrated_info = inspect_envelope(envelope)
            if migrated_info.target != info.target:
                raise MigrationError(
                    "migration changed target from {} to {}".format(
                        info.target, migrated_info.target
                    )
                )
            if migrated_info.schema_version != next_version:
                raise MigrationError(
                    "migration for {} v{} must produce v{}, got v{}".format(
                        info.target,
                        info.schema_version,
                        next_version,
                        migrated_info.schema_version,
                    )
                )
            info = migrated_info

        return envelope

    @staticmethod
    def _validate_step(target, from_version, to_version):
        if not isinstance(target, str) or not target:
            raise MigrationError("migration target must be a non-empty string")
        if not isinstance(from_version, int) or from_version < 1:
            raise MigrationError("from_version must be an integer >= 1")
        if not isinstance(to_version, int) or to_version <= from_version:
            raise MigrationError("to_version must be greater than from_version")
        if to_version != from_version + 1:
            raise MigrationError("migrations must advance one version at a time")
