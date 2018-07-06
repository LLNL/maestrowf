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

"""Collection of custom adapters for interfacing with various systems."""
import logging
from os.path import abspath, dirname, join
import yaml

from maestrowf.interfaces.mpi import GeneralParallelizer
from maestrowf.interfaces.script import \
    LocalScriptAdapter, \
    SlurmScriptAdapter, \
    SpectrumFluxScriptAdapter

__all__ = (
    "LocalScriptAdapter", "ParallelizerFactory", "SlurmScriptAdapter",
    "SpectrumFluxScriptAdapter", "ScriptAdapterFactory"
)
LOGGER = logging.getLogger(__name__)


class ScriptAdapterFactory(object):
    factories = {
        "slurm":            SlurmScriptAdapter,
        "local":            LocalScriptAdapter,
        "flux-spectrum":    SpectrumFluxScriptAdapter,
    }

    @classmethod
    def get_adapter(cls, adapter_id):
        if adapter_id.lower() not in cls.factories:
            msg = "Adapter '{0}' not found. Specify an adapter that exists " \
                  "or implement a new one mapping to the '{0}'" \
                  .format(str(adapter_id))
            LOGGER.error(msg)
            raise Exception(msg)

        return cls.factories[adapter_id]

    @classmethod
    def get_valid_adapters(cls):
        return cls.factories.keys()


class ParallelizerFactory(object):
    """ A factory for finding MPI parallelizers."""

    __recipefile__ = abspath(join(dirname(__file__), "mpi.yaml"))
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
            # If we've not loaded the recipes, do so.
            if cls.__recipes__ is None:
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
            return parallelizer(cls.__recipes__[mpi_type])
        else:
            # Otherwise, we should just return the instance of the specific
            # Parallelizer.
            # NOTE: There is a glass jaw here. If a specific Parallelizer needs
            # informattion for construction, we'll end up needing a case tree
            # here to check for types.
            return parallelizer()

    @classmethod
    def get_valid_parallelizers(cls):
        """
        Get the available MPI launchers.

        :returns: A list of available MPI launchers.
        """
        return cls._factories.keys()
