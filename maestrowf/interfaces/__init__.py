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
from importlib import import_module
import logging


__all__ = ("ParallelizerFactory", "ScriptAdapterFactory")
LOGGER = logging.getLogger(__name__)
MAESTRO_INTERFACES = "maestrowf.interfaces.script"


class ScriptAdapterFactory(object):
    """A factory class for retrieve different types of ScriptAdapters."""

    _classes = {
        "slurm":           (".slurmscriptadapter", "SlurmScriptAdapter"),
        "local":           (".localscriptadapter", "LocalScriptAdapter"),
        "flux-spectrum":   (".fluxscriptadapter", "SpectrumFluxScriptAdapter"),
    }

    @classmethod
    def get_adapter(cls, adapter_id):
        """
        Look up and retrieve a ScripttAdapter by name.

        :param adapter_id: Name of the ScriptAdapter to find.
        :returns: A ScriptAdapter class matching the specifed adapter_id.
        """
        if adapter_id.lower() not in cls._classes:
            msg = "Adapter '{0}' not found. Specify an adapter that exists " \
                  "or implement a new one mapping to the '{0}'" \
                  .format(str(adapter_id))
            LOGGER.error(msg)
            raise Exception(msg)

        module = cls._classes[adapter_id]
        return getattr(
            import_module("{}{}".format(MAESTRO_INTERFACES, module[0])),
            module[1])

    @classmethod
    def get_valid_adapters(cls):
        """
        Get all valid ScriptAdapter names.

        :returns: A list of all available keys in the ScriptAdapterFactory.
        """
        return cls._classes.keys()
