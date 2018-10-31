"""Module containing datastructures for parsing specifications."""
from importlib import import_module
from inspect import getmodule
import logging

LOGGER = logging.getLogger(__name__)


class SpecificationFactory(object):
    """A factory class to retrieve different types of Specifications."""

    _classes = {
        "yaml": {
            "latest":   (".yamlspecification", "YAMLSpecification"),
            "1.0":      (".yamlspecification", "YAMLSpecification"),
        },
    }

    @classmethod
    def get_specification(cls, spec_type, version="latest"):
        """
        Look up and retrieve a Specification by name.

        :param spec_type: Name of the Specification type to find.
        :param version: Identifier of a specific version of the 'spec_type'
        Specification. [Default: 'latest']
        :returns: A Specification class matching the specifed spec_type.
        """
        if spec_type.lower() not in cls._classes:
            msg = "Specification '{0}' not found. Specify an adapter that " \
                  "exists." \
                  .format(str(spec_type))
            LOGGER.error(msg)
            raise KeyError(msg)

        parent_module = getmodule(cls).__name__
        module = cls._classes[spec_type][version]
        return getattr(
            import_module("{}{}".format(parent_module, module[0])),
            module[1])

    @classmethod
    def get_valid_specifications(cls):
        """
        Get all valid ScriptAdapter names.

        :returns: A list of all available keys in the ScriptAdapterFactory.
        """
        return cls._classes.keys()

    @classmethod
    def get_specifications_versions(cls, spec_type):
        """
        Get available versions of a specification type.

        :params spec_type: The Specification type name to search for.
        :returns: A list of all available versions of a Specification.
        """
        if spec_type not in cls._classes:
            msg = "Specification '{0}' not found. Specify an adapter that " \
                  "exists." \
                  .format(str(spec_type))
            LOGGER.error(msg)
            raise KeyError(msg)

        return cls._classes[spec_type].keys()
