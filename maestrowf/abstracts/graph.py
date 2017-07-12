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

"""A module representing an abstract Graph base class."""
from abc import ABCMeta, abstractmethod
import six


@six.add_metaclass(ABCMeta)
class Graph(object):
    """An abstract graph data structure."""

    # NOTE: fdinatal -- 04/07/2017
    # This class mandates that a graph class be searchable currently.
    # That requirement should be filtered out into another abstract interface
    # most likely (think C# interfaces). I could imagine cases where a coder/
    # developer would want a leaner object without the frills.

    @abstractmethod
    def add_node(self, name, obj):
        """
        Method to add a node to the graph.

        :param name: String identifier of the node.
        :param obj: An object representing the value of the node.
        """
        pass

    @abstractmethod
    def add_edge(self, src, dest):
        """
        Add the edge (src, dest) to the graph.

        :param src: Source vertex name.
        :param dest: Destination vertex name.
        """
        pass

    @abstractmethod
    def remove_edge(self, src, dest):
        """
        Remove edge (src, dest) from the graph.

        :param src: Source vertex name.
        :param dest: Destination vertex name.
        """
        pass
