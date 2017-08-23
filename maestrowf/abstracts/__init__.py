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

"""
The core abstract APIs that define various class behaviors.

This module contains all of the abstract classes and APIs for defining objects.
Abstracts include abstract data stuctures (like a graph), APIs for concepts
such as queueing adapters and environment APIs, as well as fundamental data
structures like a SimObject.
"""
# NOTE: Some of these abstracts will be moved in the future. The Graph abstract
# class does not belong here, and should be moved to something more general.
# NOTE: The SimObject base class may not be required, since it basically
# just requires objects to be dictionaries.

from maestrowf.abstracts.abstractclassmethod import abstractclassmethod
from maestrowf.abstracts.envobject import Dependency, Source, Substitution
from maestrowf.abstracts.graph import Graph
from maestrowf.abstracts.simobject import SimObject
from maestrowf.abstracts.specification import Specification


__all__ = ("abstractclassmethod", "Dependency", "Graph", "SimObject",
           "Singleton", "Source", "Specification", "Substitution")


class _Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args,
                                                                  **kwargs)
        return cls._instances[cls]


class Singleton(_Singleton('SingletonMeta', (object,), {})):
    """Single type to allow for classes to be typed as a singleton."""

    pass
