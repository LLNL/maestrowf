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

"""The collection of basic classes that can be used for an environment."""

from abc import ABCMeta, abstractmethod
import logging
import six

from maestrowf.abstracts.simobject import SimObject

logger = logging.getLogger(__name__)


@six.add_metaclass(ABCMeta)
class EnvObject(SimObject):
    """
    An abstract class representing objects that exist in a study's environment.

    The EnvObject is meant to be used to represent entities in the larger
    environment that affect the execution of a study (and therefore jobs).
    This abstact base class should be used to represent things such as data
    dependencies, code dependencies, variables, aliases, etc. The only method
    we require is _verify, to allow users to verify that they've provided the
    minimal information for the object to be valid.
    """

    @abstractmethod
    def _verify(self):
        """
        Verify that the object is valid.

        Subclasses that inherit from the EnvObject abstract class are expected
        to provide a method for asserting that the contents contained within
        the object are valid. Valid can range anywhere from asserting that all
        expected member variables are populated to asserting specific values of
        members, etc.

        :returns: True if the EnvObject is verified, False otherwise.
        """
        pass

    def _verification(self, error):
        """
        A wrapper method for verifying for using a custom error message.

        :param error: String containing a custom error message.
        """
        if not self._verify():
            logger.exception(error)
            raise ValueError(error)


@six.add_metaclass(ABCMeta)
class Substitution(EnvObject):
    """Abstract class representing classes that perform value replacements."""

    @abstractmethod
    def substitute(self, data):
        """
        Perform a replacement of some substring into data.

        The method takes the input string data and performs a replacement. This
        API is used to represent concepts such as variables or parameters that
        would want to be replaced within the string data.

        :param data: A string to perform a replacement on.
        :returns: A string equal to the original string data with substitutions
            made (if any were performed).
        """
        pass


@six.add_metaclass(ABCMeta)
class Source(EnvObject):
    """
    Abstract class representing classes that alter environment sourcing.

    WARNING: The API for this class is still in development.
    The Source environment class is meant to provide a way to programmatically
    set environment settings that binaries or other scripts may require in the
    workflow. Such settings that are intended to be captured are:
        - Exporting of shell/environment variables (using 'export')
        - Setting of an environment package with the 'use' command
    """

    @abstractmethod
    def apply(self, data):
        """
        Apply the Source to some string data.

        Subclasses of Source should use this method in order to apply an
        environment alterating change. The 'data' parameter should be a string
        representing a command to apply Source to or a list of other comands
        that Source should be included with.

        :param data: A string representing a command or set of other sources.
        :returns: A string with the Source applied.
        """
        # NOTE: This functionality has not been settled yet. The use of this
        # class or this design may not be the best for applying script sources
        # to an environment.
        pass


@six.add_metaclass(ABCMeta)
class Dependency(Substitution):
    """
    Abstract object representing a dependency.

    The Dependency base class is intended to be used to capture external items
    the workflow is dependent on. These items include (but are not limited to):
        - Remotely stored repositories (such as bitbucket)
        - Paths located on the filesystem that hold required files or binaries
        - Binaries that are required to be installed using a specific package
          manager
        - External APIs that a workflow needs to pull data from

    The goal of this base class is to make it so that this package is able to
    pull exernal dependencies in a consistent manner.
    """

    @abstractmethod
    def acquire(self, substitutions=None):
        """
        Acquire the dependency as specfied by the class instance.

        Subclasses that implement this interface should raise exceptions during
        acquisition should they be unable to retrieve their specified
        dependency. It is assumed that if acquiring throws an exception that
        the study cannot proceed forward.

        :param substitutions: List of Substitution objects that can be applied.
        """
        pass
