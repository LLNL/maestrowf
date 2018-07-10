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
"""A module that provides interfaces to multiple MPI launchers."""
import logging
from os.path import abspath, dirname, join
import yaml

from maestrowf.interfaces.mpi.commandparallelizer import CommandParallelizer
from maestrowf.abstracts.interfaces import Parallelizer

__all__ = ("CommandParallelizer", "GeneralParallelizer", "ParallelizerFactory")
LOGGER = logging.getLogger(__name__)


class GeneralParallelizer(Parallelizer):
    """A class for general parallel command generation."""

    def __init__(self, cmd, recipe):
        """
        Construct an instance of the GeneralParallelizer.

        :param cmd: The parallel command to be used.
        :param recipe: A dictionary containing the generalized recipe format.
        """
        self._cmd = cmd
        self._recipe = recipe

    def get_parallelize_command(self, cmd, resources):
        """
        Generate the parallelization segement of the command line.

        :param cmd: Command string to substitute parallel command into.
        :param resources: Dict of resources to be used by parallel commands.
        :returns: A string of the parallelize command configured using the
        specified resources.
        """
        pass


class ParallelizerFactory(object):
    """A factory for finding MPI parallelizers."""

    __recipefile__ = abspath(join(dirname(__file__), "recipes", "mpi.yaml"))
    __recipes__ = None

    _factories = {
        "srun": GeneralParallelizer,
    }

    @classmethod
    def get_parallelizer(cls, mpi_type):
        """
        Get the Parallelizer for the specfied MPI type.

        :param mpi_type: The MPI binary to parallelize with.
        :returns: A Parallelizer object for the specified MPI type.
        """
        # Check that the requested parallel command is one we support.
        if mpi_type.lower() not in cls.factories:
            msg = "Parallelizer '{0}' not found. Specify an adapter that " \
                  "exists or implement a new one mapping to the '{0}'" \
                  .format(str(mpi_type))
            LOGGER.error(msg)
            raise Exception(msg)

        # Check out factory for the object we need.
        parallelizer = cls._factories[mpi_type]

        # If we see the general case that uses recipes, do the following:
        if isinstance(parallelizer, GeneralParallelizer):
            LOGGER.debug("'%s' uses the GeneralParallelizer.", mpi_type)
            # If we've not loaded the recipes, do so.
            if cls.__recipes__ is None:
                LOGGER.info("Recipes not loaded. Loading from '%s'",
                            cls.__recipefile__)
                cls.__recipes__ = yaml.load(cls.__recipefile__)

            # We also need to have the recipe for the MPI flavor we requested.
            # If it's not in our recipes, we can continue -- abort.
            if mpi_type not in cls.__recipes__:
                msg = "'{0}' uses a generalized recipe but the recipe does " \
                      "exist! Please make sure that your recipes are up to" \
                      "date. Recipe file location = {1}" \
                      .format(mpi_type, cls.__recipefile__)
                LOGGER.exception(msg)
                raise KeyError(msg)

            # Otherwise, construct and return the general parallizer.
            return parallelizer(mpi_type, cls.__recipes__[mpi_type])
        else:
            # Otherwise, we should just return the instance of the specific
            # Parallelizer.
            # NOTE: There is a glass jaw here. If a specific Parallelizer needs
            # informattion for construction, we'll end up needing a case tree
            # here to check for types.
            LOGGER.debug("'%s' uses a custom Parallelizer.", mpi_type)
            return parallelizer()

    @classmethod
    def get_valid_parallelizers(cls):
        """
        Get the available MPI launchers.

        :returns: A list of available MPI launchers.
        """
        return cls._factories.keys()
