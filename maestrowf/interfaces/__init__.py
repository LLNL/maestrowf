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

from maestrowf.interfaces.script import \
    LocalScriptAdapter, \
    SlurmScriptAdapter, \
    SpectrumFluxScriptAdapter

__all__ = (
    "LocalScriptAdapter", "SlurmScriptAdapter", "SpectrumFluxScriptAdapter",
    "ScriptAdapterFactory"
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
