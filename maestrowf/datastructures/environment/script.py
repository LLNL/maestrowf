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

"""Class representing the sourcing of a script."""

import logging
import re

from maestrowf.abstracts import Source

logger = logging.getLogger(__name__)


class Script(Source):
    """Script class for applying changes to the execution environment."""

    # TODO: Sourcing is an issue. We need to figure out a way to handle this.
    def __init__(self, source):
        """
        Initialize the Script class.

        :params source: The command for changing the execution environment.
        """
        self.source = source
        self._verification("Script initialized without complete settings. Set"
                           " source before calling methods.")

    def apply(self, cmds):
        """
        Apply the Script source to the specified list of commands.

        :param cmds: List of commands to add source to.
        :returns: List of commands with the source prepended.
        """
        return [self.source] + list(cmds)

    def _verify(self):
        """
        Verify the Script object's contents.

        :returns: True if the Script object is valid, False otherwise.
        """
        valid_param_pattern = re.compile(r"\w+")
        return bool(re.search(valid_param_pattern, self.source))
