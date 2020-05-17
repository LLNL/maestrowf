###############################################################################
# Copyright (c) 2017, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
# Written by Francesco Di Natale, dinatale3@llnl.gov.
#
# LLNL-CODE-734340
# All rights reserved.
# This file is part of MaestroWF, Version: 1.0.0.
#
# For details, see https://github.com/LLNL/maestrowf.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################

"""Classes that represent the environment of a study."""

import logging

from maestrowf.abstracts import Dependency, Source, Substitution

LOGGER = logging.getLogger(__name__)


class StudyEnvironment:
    """
    StudyEnvironment for managing a study environment.

    The StudyEnvironment provides the context where all study
    steps can find variables, sources, dependencies, etc.
    """

    def __init__(self):
        """Initialize an empty StudyEnvironment."""
        # Types of environment objects.
        self.substitutions = {}
        self.labels = {}
        self.sources = []
        self.dependencies = {}

        # Private members
        self._tokens = set()
        self._names = set()
        # Boolean that tracks if dependencies have been acquired.
        self._is_set_up = False

        LOGGER.debug("Initialized an empty StudyEnvironment.")

    def __bool__(self):
        """
        Override for the __bool__ operator.

        :returns: True if the StudyEnvironment instance has values, False
            otherwise.
        """
        return bool(self._names)

    @property
    def is_set_up(self):
        """
        Check that the StudyEnvironment is set up.

        :returns: True is the instance is set up, False otherwise.
        """
        return self._is_set_up

    def add(self, item):
        """
        Add the item parameter to the StudyEnvironment.

        :param item: EnvObject to be added to the environment.
        """
        # TODO: Need to revist this to make this better. A label can get lost
        # because the necessary variable could have not been added yet
        # and there's too much of a need to process a dependency first.
        name = None
        LOGGER.debug("Calling add with %s", str(item))
        if isinstance(item, Dependency):
            LOGGER.debug("Adding %s of type %s.", item.name, type(item))
            LOGGER.debug("Value: %s.", item.__dict__)
            self.dependencies[item.name] = item
            name = item.name
            self._is_set_up = False
        elif isinstance(item, Substitution):
            LOGGER.debug("Value: %s", item.value)
            LOGGER.debug("Tokens: %s", self._tokens)
            name = item.name
            LOGGER.debug("Adding %s of type %s.", item.name, type(item))
            if (
                    isinstance(item.value, str) and
                    any(token in item.value for token in self._tokens)):
                LOGGER.debug("Label detected. Adding %s to labels", item.name)
                self.labels[item.name] = item
            else:
                self._tokens.add(item.token)
                self.substitutions[item.name] = item
        elif isinstance(item, Source):
            LOGGER.debug("Adding source %s", item.source)
            LOGGER.debug("Item source: %s", item.source)
            self.sources.append(item)
        else:
            error = "Received an item of type {}. Expected an item of base " \
                    "type Substitution, Source, or Dependency." \
                    .format(type(item))
            LOGGER.exception(error)
            raise TypeError(error)

        if name and name in self._names:
            error = "A duplicate name '{}' has been detected. All names " \
                    "must be unique. Aborting.".format(name)
            LOGGER.exception(error)
            raise ValueError(error)
        else:
            LOGGER.debug("{} added to set of names.".format(name))
            self._names.add(name)

    def find(self, key):
        """
        Find the environment object labeled by the specified key.

        :param key: Name of the environment object to find.
        :returns: The environment object labeled by key, None if key is not
            found.
        """
        LOGGER.debug("Looking for '%s'...", key)
        if key in self.dependencies:
            LOGGER.debug("Found '%s' in environment dependencies.", key)
            return self.dependencies[key]

        if key in self.substitutions:
            LOGGER.debug("Found '%s' in environment substitutions.", key)
            return self.substitutions[key]

        if key in self.labels:
            LOGGER.debug("Found '%s' in environment labels.", key)
            return self.labels[key]

        LOGGER.debug("'%s' not found -- \n%s", key, self)
        return None

    def remove(self, key):
        """
        Remove the environment object labeled by the specified key.

        :param key: Name of the environment object to remove.
        :returns: The environment object labeled by key.
        """
        LOGGER.debug("Looking to remove '%s'...", key)

        if key not in self._names:
            return None

        _ = self.dependencies.pop(key, None)
        if _ is not None:
            self._names.remove(key)
            return _

        _ = self.substitutions.pop(key, None)
        if _ is not None:
            self._names.remove(key)
            return _

        _ = self.labels.pop(key, None)
        if _ is not None:
            self._names.remove(key)
            return _

        LOGGER.debug("'%s' not found -- \n%s", key, self)
        return None

    def acquire_environment(self):
        """Acquire any environment items that may be stored remotely."""
        if self._is_set_up:
            LOGGER.info("Environment already set up. Returning.")
            return

        LOGGER.debug("Acquiring dependencies")
        for dependency, value in self.dependencies.items():
            LOGGER.info("Acquiring -- %s", dependency)
            value.acquire(substitutions=self.substitutions.values())

        self._is_set_up = True

    def apply_environment(self, item):
        """
        Apply the environment to the specified item.

        :param item: String to apply environment to.
        :returns: String with the environment applied.
        """
        if not item:
            return item

        LOGGER.debug("Applying environment to %s", item)
        LOGGER.debug("Processing labels...")
        for label, value in self.labels.items():
            LOGGER.debug("Looking for %s in %s", label, item)
            item = value.substitute(item)
            LOGGER.debug("After substitution: %s", item)

        LOGGER.debug("Processing dependencies...")
        for label, dependency in self.dependencies.items():
            LOGGER.debug("Looking for %s in %s", label, item)
            item = dependency.substitute(item)
            LOGGER.debug("After substitution: %s", item)
            LOGGER.debug("Acquiring %s.", label)

        LOGGER.debug("Processing substitutions...")
        for substitution, value in self.substitutions.items():
            LOGGER.debug("Looking for %s in %s", substitution, item)
            item = value.substitute(item)
            LOGGER.debug("After substitution: %s", item)

        return item
