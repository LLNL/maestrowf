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

"""Class representing a file system path dependency."""

import logging
import os
import re

from maestrowf.abstracts import Dependency

logger = logging.getLogger(__name__)


class PathDependency(Dependency):
    """Environment PathDependency class for substituting a path dependency."""

    def __init__(self, name, value, token='$'):
        """
        Initialize the PathDependency class.

        The PathDependency represents a dependency that is stored in the local
        file system. These dependencies can be things like shared group folders
        or local directories in user space which contain items the study needs
        to run. Otherwise, this class operates like the Variable class and
        represents substrings that can be present within String data that are
        meant to be replaced. The general format that such items take is
        generally expressed as '<token>(<name>)', and will be replaced
        with the value specified.

        :params name: String name that refers to a PathDependency instance.
        :params value: The value to substitute for the PathDependency instance.
        :params token: String of expected character(s) that appear at the
            beginning of a substring representing the dependency variable.
        """
        self.name = name
        self.value = os.path.abspath(value)
        self.token = token

        self._verification("PathDependency initialized without complete"
                           " settings. Set required [name, value] before "
                           "calling methods.")
        self._is_acquired = False

    def get_var(self):
        """
        Get the variable representation of the dependency's name.

        :returns: String of the Dependencies's name in token form.
        """
        return "{}({})".format(self.token, self.name)

    def substitute(self, data):
        """
        Substitute the dependency's value for its notation.

        :param data: String to substitute dependency into.
        :returns: String with the dependency's name replaced with its value.
        """
        if not self._verify():
            error = "Ensure that all required fields (name, value)," \
                    "are populated and that value is a valid path."
            logger.exception(error)
            raise ValueError(error)

        logger.debug("%s: %s", self.get_var(),
                     data.replace(self.get_var(), self.value))
        return data.replace(self.get_var(), self.value)

    def acquire(self, substitutions=None):
        """
        Acquire the dependency specified by the PathDependency.

        The PathDependency is simply a path that already exists, so the method
        doesn't actually acquire anything, but it does verify that the path
        exists.

        :param substitutions: List of Substitution objects that can be applied.
        """
        if self._is_acquired:
            return

        if not self._verify():
            error = "Ensure that all required fields (name, " \
                    "value), are populated and that value is a " \
                    "valid path."
            logger.exception(error)
            raise ValueError(error)

        if not os.path.exists(self.value):
            error = "The specified path '{}' does not exist.".format(self.name)
            logger.exception(error)
            raise ValueError(error)

        self._is_acquired = True

    def _verify(self):
        """
        Verify that the necessary Dependency fields are populated.

        :returns: True if Dependency is valid, False otherwise.
        """
        valid_param_pattern = re.compile(r"\w+")
        return bool(re.search(valid_param_pattern, self.name) and
                    re.search(valid_param_pattern, self.value) and
                    self.token)

    def __str__(self):
        """
        Generate the string representation of the object.

        :returns: A string with the token form of the variable.
        """
        return str(self.get_var())
