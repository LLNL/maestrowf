"""Schema migration registry for primitive document envelopes.

The registry upgrades one target payload schema version at a time. A migration
registered for version ``N`` must produce version ``N + 1`` for the same
``target``. Chaining small migrations keeps each schema change reviewable,
gives tests a stable place to pin every historical transition, and lets loaders
upgrade older documents by repeatedly applying the same simple rule.
"""

import copy

from maestrowf.serialization.envelope import (
    inspect_envelope,
    validate_envelope,
)
from maestrowf.serialization.errors import FutureVersionError, MigrationError


class MigrationRegistry:
    """Register and apply target-specific document schema migrations.

    Migration functions operate on full primitive envelopes, not only on the
    payload. That lets a target migration update payload data and the envelope's
    ``schema_version`` together while the generic registry verifies that the
    migration did not change the target or skip a version.
    """

    def __init__(self):
        """Create an empty migration registry."""
        self._migrations = {}

    def register(self, target, from_version, to_version=None, func=None):
        """Register a one-step migration function.

        If called without ``func``, this returns a decorator. Migration
        functions receive a primitive envelope and must return a primitive
        envelope for the next schema version.

        :param target: Open string identifying the payload contract that owns
            the migration.
        :param from_version: Source schema version. Persisted schema versions
            start at ``1``; ``0`` is reserved for unversioned/draft/legacy data.
        :param to_version: Destination schema version. When omitted, it
            defaults to ``from_version + 1``.
        :param func: Optional migration callable. If omitted, ``register``
            returns a decorator for the callable.
        :returns: The registered migration callable when ``func`` is provided,
            otherwise a decorator that registers one callable.
        :raises MigrationError: If the target/version step is invalid or a
            migration has already been registered for the same step.
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
        """Upgrade an envelope to the current schema version for its target.

        The input envelope is deep-copied before validation and migration, so
        callers keep their original value unchanged.

        :param envelope: Primitive document envelope loaded from storage.
        :param current_version: Highest schema version supported by the
            target-specific loader.
        :returns: A validated primitive envelope at ``current_version``.
        :rtype: dict
        :raises FutureVersionError: If the envelope schema version is newer
            than ``current_version``.
        :raises MigrationError: If a required migration is missing or a
            migration returns an invalid next envelope.
        """
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
        """Validate that a migration registration advances exactly one step."""
        if not isinstance(target, str) or not target:
            raise MigrationError("migration target must be a non-empty string")
        if not isinstance(from_version, int) or from_version < 1:
            raise MigrationError("from_version must be an integer >= 1")
        if not isinstance(to_version, int) or to_version <= from_version:
            raise MigrationError("to_version must be greater than from_version")
        if to_version != from_version + 1:
            raise MigrationError("migrations must advance one version at a time")
