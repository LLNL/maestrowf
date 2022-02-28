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
import pkgutil
import inspect
from maestrowf.abstracts.interfaces import ScriptAdapter, ParallelizeCmd

__all__ = ("ScriptAdapterFactory",)
LOGGER = logging.getLogger(__name__)


def iter_adapters():
    """
    Based off of packaging.python.org loop over a namespace and find the
    modules. This has been adapted for this particular use case of loading
    all classes implementing ScriptAdapter loaded from all modules in
    maestrowf.interfaces.script.
    :return: an iterable of the classes existing in the namespace
    """
    # get loader for the script adapter package
    loader = pkgutil.get_loader('maestrowf.interfaces.script')
    # get all of the modules in the package
    mods = [(name, ispkg) for finder, name, ispkg in pkgutil.iter_modules(
            loader.load_module('maestrowf.interfaces.script').__path__,
            loader.load_module('maestrowf.interfaces.script').__name__ + ".")]

    cs = []
    for name, _ in mods:
        # get loader for every module
        m = pkgutil.get_loader(name).load_module(name)
        # get all classes that implement ScriptAdapter and are not abstract
        for n, cls in m.__dict__.items():
            if isinstance(cls, type) and issubclass(cls, ScriptAdapter) and \
                    not inspect.isabstract(cls):
                cs.append(cls)
                print("FOUND CLASS '{}' with key '{}'".format(cls.__name__, cls.key))
            if isinstance(cls, type) and issubclass(cls, ScriptAdapter):
                print("FOUND CLASS '{}'".format(cls.__name__))
                LOGGER.debug("Found class '{}'".format(cls.__name__))

    return cs


def iter_parallel_cmds():
    """
    Based off of packaging.python.org loop over a namespace and find the
    modules. This has been adapted for this particular use case of loading
    all classes implementing ParallelizeCmd loaded from all modules in
    maestrowf.interfaces.script.
    :return: an iterable of the classes existing in the namespace
    """
    # get loader for the script adapter package
    loader = pkgutil.get_loader('maestrowf.interfaces.script')
    # get all of the modules in the package
    mods = [(name, ispkg) for finder, name, ispkg in pkgutil.iter_modules(
            loader.load_module('maestrowf.interfaces.script').__path__,
            loader.load_module('maestrowf.interfaces.script').__name__ + ".")]

    cs = []
    for name, _ in mods:
        # get loader for every module
        m = pkgutil.get_loader(name).load_module(name)
        # get all classes that implement ParallelizeCmd and are not abstract
        for n, cls in m.__dict__.items():
            if isinstance(cls, type) and issubclass(cls, ParallelizeCmd) and \
                    not inspect.isabstract(cls):
                cs.append(cls)
                print("FOUND CLASS '{}' with key '{}'".format(cls.__name__, cls.key))
            if isinstance(cls, type) and issubclass(cls, ParallelizeCmd):
                print("FOUND CLASS '{}'".format(cls.__name__))
                LOGGER.debug("Found class '{}'".format(cls.__name__))

    return cs


class ScriptAdapterFactory(object):
    factories = {
       adapter.key: adapter for adapter in iter_adapters()
    }

    parallel_cmd_factories = {
        parallel_cmd.key: parallel_cmd for parallel_cmd in iter_parallel_cmds()
    }

    @classmethod
    def get_adapter(cls, adapter_id, parallel_type=None):
        if adapter_id.lower() not in cls.factories:
            msg = "Adapter '{0}' not found. Specify an adapter that exists " \
                  "or implement a new one mapping to the '{0}'" \
                  .format(str(adapter_id))
            LOGGER.error(msg)
            raise Exception(msg)

        # adapter = cls.factories[adapter_id]

        # # Attach any specified parallelize cmd generators
        # if parallel_type and adapter_id in cls.parallel_cmd_factories:
        #     adapter.register_parallelize_command(
        #         cls.parallel_cmd_factories[adapter_id]
        #     )

        print(f"Returning: {cls.factories[adapter_id]}")
        return cls.factories[adapter_id]

    @classmethod
    def get_valid_adapters(cls):
        return cls.factories.keys()
