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

"""Class for handling Variable substitutions."""

import logging

from maestrowf.abstracts import Substitution

logger = logging.getLogger(__name__)


class Variable(Substitution):
    """
    Environment Variable class capable of substituting itself into strings.

    Derived from the Substitution EnvObject class which requires that a
    substitution be able to inject itself into data.
    """

    def __init__(self, name, value, token='$'):
        """
        Initialize the Variable class.

        The Variable represents substrings that can be present within String
        data that are meant to be replaced. The general format that such items
        take is generally expressed as '<token>(<name>)', and will be replaced
        with the value specified.

        :params name: String name that refers to a Variable instance.
        :params value: The value to substitute for the Variable instance.
        :params token: String of expected character(s) that appear at the
            beginning of a substring representing the variable.
        """
        self.name = name
        self.value = value
        self.token = token

        if not self._verify():
            msg = "Variable initialized without complete settings. Set " \
                           "required [name, value] before calling methods."
            logger.exception(msg)
            raise ValueError(msg)

    def get_var(self):
        """
        Get the variable representation of the variable's name.

        :returns: String of the Variable's name in token form.
        """
        return "{}({})".format(self.token, self.name)

    def substitute(self, data):
        """
        Substitute the variable's value for its notation.

        :param data: String to substitute variable into.
        :returns: String with the variable's name replaced with its value.
        """
        self._verification("Attempting to substitute a variable that is not"
                           " complete.")
        logger.debug("%s: %s", self.get_var(),
                     data.replace(self.get_var(), str(self.value)))
        return data.replace(self.get_var(), str(self.value))

    def _verify(self):
        """
        Verify that the necessary Variable fields are populated.

        :returns: True if Variable is valid, False otherwise.
        """
        return bool(self.name) and bool(self.value)

    def __str__(self):
        """
        Generate the string representation of the objects.

        :returns: A string with the token form of the variable.
        """
        return self.get_var()
