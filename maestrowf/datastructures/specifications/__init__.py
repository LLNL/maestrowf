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
    def get_specification(cls, spec_name, version="latest"):
        """
        Look up and retrieve a Specification by name.

        :param spec_name: Name of the Specification to find.
        :returns: A Specification class matching the specifed spec_name.
        """
        if spec_name.lower() not in cls._classes:
            msg = "Specification '{0}' not found. Specify an adapter that " \
                  "exists." \
                  .format(str(spec_name))
            LOGGER.error(msg)
            raise Keyerror(msg)

        parent_module = getmodule(cls).__name__
        module = cls._classes[spec_name][version]
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
    def get_specifications_versions(cls, spec_name):
        """
        Get available versions of a specification type.

        :returns: A list of all available versions of a Specification.
        """
        if spec_name not in cls._classes:
            msg = "Specification '{0}' not found. Specify an adapter that " \
                  "exists." \
                  .format(str(spec_name))
            LOGGER.error(msg)
            raise KeyError(msg)

        return cls._classes[spec_name].keys()
