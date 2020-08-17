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

"""Module that contains the implemenation of a Directed-Acyclic Graph."""

from collections import deque, OrderedDict
import logging
from math import sqrt

from maestrowf.abstracts.graph import Graph

logger = logging.getLogger(__name__)


class DAG(Graph):
    """
    A directed acyclic graph (DAG) data structure.

    The implementation of this DAG uses an adjacency map with a map to
    index the values (or objects) at each node.
    """

    def __init__(self):
        """Initialize the DAG data structure internals."""
        self.adjacency_table = OrderedDict()
        self.values = OrderedDict()

    def add_node(self, name, obj):
        """
        Add node 'name' to the DAG.

        :param name: String identifier of the node.
        :param obj: An object representing the value of the node.
        """
        logging.debug("Adding %s...", name)
        if name in self.values:
            logger.warning("Node %s already exists. Returning.",
                           name)
            return

        logger.debug("Node %s added. Value is of type %s.", name, type(obj))
        self.values[name] = obj
        self.adjacency_table[name] = []

    def add_edge(self, src, dest):
        """
        Add an edge to the DAG if edge (src, dest) is a valid edge.

        :param src: Source vertex name.
        :param dest: Destination vertex name.
        """
        # Disallow loops to the same node.
        if src == dest:
            msg = "Cannot add self referring cycle edge ({}, {})" \
                  .format(src, dest)
            logger.error(msg)
            return

        # Disallow adding edges to the graph before nodes are added.
        error = "Attempted to create edge ({src}, {dest}), but node {node}" \
                " does not exist."
        if src not in self.adjacency_table:
            error = error.format(src=src, dest=dest, node=src)
            logger.error(error)
            raise ValueError(error)

        if dest not in self.adjacency_table:
            logger.error(error, src, dest, dest)
            return

        if dest in self.adjacency_table[src]:
            logger.debug("Edge (%s, %s) already in DAG. Returning.", src, dest)
            return

        # If dest is not already and edge from src, add it.
        self.adjacency_table[src].append(dest)
        logging.debug("Edge (%s, %s) added.", src, dest)

        # Check to make sure we've not created a cycle.
        if self.detect_cycle():
            msg = "Adding edge ({}, {}) crates a cycle.".format(src, dest)
            logger.error(msg)
            raise Exception(msg)

    def remove_edge(self, src, dest):
        """
        Remove edge (src, dest) from the DAG.

        :param src: Source vertex name.
        :param dest: Destination vertex name.
        """
        if src not in self.adjacency_table:
            logger.warning("Attempted to remove an edge (%s, %s), but %s"
                           " does not exist.", src, dest, src)
            return

        if dest not in self.adjacency_table:
            logger.warning("Attempted to remove an edge from (%s, %s), but %s"
                           " does not exist.", src, dest, dest)
            return

        logging.debug("Removing edge (%s, %s).", src, dest)
        self.adjacency_table[src].remove(dest)

    def dfs_subtree(self, src, par=None):
        """
        Create a subtree of the DAG starting at src in DFS order.

        :param src: Source node name to begin search.
        :param par: Name of parent node to the specified source node.
        :returns: A list representing the path taken by DFS.
        :returns: A dictionary containing a mapping from node to parent node.
        """
        path = [src]
        parent = {src: par}
        for node in self.adjacency_table[src]:
            parent[node] = src
            subpath, children = self.dfs_subtree(node, src)
            path = path + subpath
            parent.update(children)

        return path, parent

    def bfs_subtree(self, src):
        """
        Create a subtree of the DAG starting at src in BFS order.

        :param src: Source node name to begin search.
        :returns: A list representing the path taken by BFS.
        :returns: A dictionary containing a mapping from node to parent node.
        """
        queue = deque([src])
        path = [src]
        parent = {src: None}

        while queue:
            root = queue.popleft()
            for node in self.adjacency_table[root]:
                if node in path:
                    continue

                queue.append(node)
                parent[node] = root
                path.append(node)

        return path, parent

    def _topological_sort(self, v, visited, stack):
        """
        Recur through the nodes to perform a toplogical sort.

        :param v: The vertex previously visited.
        :param visited: A dict of visited statuses.
        :param stack: The current stack of vertices that have been sorted.
        :returns: A list of the DAG's nodes in topologically sorted order.
        """
        # Mark the node as visited.
        visited[v] = True

        # Recur through the children, visiting children who have not yet been
        # visited.
        for e in self.adjacency_table[v]:
            if not visited[e]:
                self._topological_sort(e, visited, stack)

        # Prepend v to the front of the list.
        stack.appendleft(v)

    def topological_sort(self):
        """
        Perform a topological ordering of the vertices in the DAG.

        :returns: A list of the vertices sorted in topological order.
        """
        v_stack = deque()
        v_visited = {key: False for key in self.values.keys()}

        for v in self.values:
            if not v_visited[v]:
                self._topological_sort(v, v_visited, v_stack)

        return list(v_stack)

    def detect_cycle(self):
        """Detect if the DAG contains a cycle."""
        visited = set()
        rstack = set()
        for v in self.values:
            if v not in visited:
                logging.debug("Visting '%s'...", v)
                if self._detect_cycle(v, visited, rstack):
                    logging.debug("Cycle detected. Origin = '%s'", v)
                    return True
        logger.debug("No cycles found -- returning.")
        return False

    def _detect_cycle(self, v, visited, rstack):
        """
        Recurse through nodes testing for loops.

        :param v: Name of source vertex to search from.
        :param visited: Set of the nodes we've visited so far.
        :param rstack: Set of nodes currently on the path.
        """
        visited.add(v)
        rstack.add(v)

        for c in self.adjacency_table[v]:
            if c not in visited:
                logging.debug("Visting node '%s' from '%s'.", c, v)
                if self._detect_cycle(c, visited, rstack):
                    logger.debug("Cycle detected --\n"
                                 "rstack = %s\n"
                                 "visited = %s",
                                 rstack, visited)
                    return True
            elif c in rstack:
                logger.debug("Cycle detected ('%s' in rstack)--\n"
                             "rstack = %s\n"
                             "visited = %s",
                             c, rstack, visited)
                return True
        rstack.remove(v)
        logger.debug("No cycle originating from '%s'", v)
        return False

    def export_dag_vis(self, dag_basename, draw_opts):
        """
        Export hierarchical representation of this study's dag to the list of
        formats specified in draw_opts.

        :param dag_basename: Basename of output file, in study output path
        :param draw_opts: specifies one or more file output formats.
                          mpl (matplotlib png), mpl-dot (dot layout mpl), dot
                          (graphviz dot file), graphml (graphml file)

        NOTE: must this re-call topological sort for safety?
        NOTE: Add optional node annotations/attributes (colors, shape, etc)
        NOTE: Add skeleton only format (unexpanded steps)
        NOTE: Add partial expansion of dag -> large workflows
        NOTE: What about node attributes when here are too many parameters
              to enumerate?
        """

        logger.debug("Exporting hierarchical representation of dag")

        # Put these at the top of file, maybe decorate this function to handle
        # the disablement?
        try:
            import matplotlib.pyplot as plt
            import networkx as nx

        except ImportError:
            logger.exception("Couldn't import graph drawing utilities; "
                             "disabling graph visualzation.")
            return

        try:
            import pygraphviz   # Used indirectly, only imported for checking
            from networkx.drawing.nx_agraph import write_dot
            have_pygv = True

        except ImportError:
            logger.exception("Error importing pygraphviz: dot "
                             "layout/output disabled.")

            have_pygv = False

        dagnx = nx.DiGraph()

        nodelist = self.topological_sort()
        node_labels = {}
        for idx, node in enumerate(nodelist):

            if node == '_source':
                node_label = 'Study'  # Try to get study name instead?
            else:
                this_step = self.values[node].step
                node_label = '{}\n'.format(this_step.base_name)
                for var, value in this_step.param_vals.items():
                    varname = var[2:-1]
                    node_label += '{}:{}\n'.format(varname, value)

                logger.debug("Adding label to node {}: {}".format(node,
                                                                  node_label))

            node_labels[node] = node_label  # draw these later
            dagnx.add_node(node,
                           label=node_label)

        for node in nodelist:
            edges = self.adjacency_table[node]

            dagnx.add_edges_from([(node, child) for child in edges])
            logger.debug("Node {} has children: {}".format(node, edges))

        # Compute node positions for two layouts
        # Note: work on something better for sizing/layout than these hacks
        # NOTE: check if this longest path computation is expensive
        longest_chain = len(nx.algorithms.dag_longest_path(dagnx))
        pos_spring = nx.spring_layout(dagnx, k=1/sqrt(longest_chain))

        # Convert to pygraphviz agraph for dot layout
        if have_pygv:
            pos_dot = nx.nx_agraph.pygraphviz_layout(dagnx, prog='dot')
        else:
            # Fail-safe for matplotlib rendering
            pos_dot = pos_spring

        for viz_format in draw_opts:

            # For matplotlib, have to do extra work to compute image size
            if viz_format == "mpl" or viz_format == "mpl-dot":
                fig, ax = plt.subplots(figsize=(3*longest_chain,
                                                2*longest_chain))

            if viz_format == "mpl" or viz_format == "graphml":
                pos = pos_spring
            else:
                pos = pos_dot

            if viz_format == "mpl" or viz_format == "mpl-dot":
                # Possible to iteratively compute node size and figure size?
                nx.draw_networkx(dagnx,
                                 pos=pos,
                                 ax=ax,
                                 labels=node_labels,
                                 node_size=500)
                # May need to render labels separately?
                # nx.draw(dagnx, with_labels=False)
                # nx.draw_networkx_labels(dagnx,
                plt.savefig(dag_basename + '.png', dpi=150)

            if viz_format == "dot" and have_pygv:
                # Possible to pass networkx/pygraphviz agraph object around
                # when imports aren't available?
                nx.nx_agraph.write_dot(dagnx, dag_basename + '.dot')

            if viz_format == "graphml" or viz_format == "graphml-dot":
                # NOTE: find implementation that avoids this copy
                graphml_dag = dagnx
                # Add positions as node attributes (NEEDS VERIFICATION)
                for node, (x, y) in pos.items():
                    graphml_dag.node[node]['x'] = float(x)
                    graphml_dag.node[node]['y'] = float(y)

                    nx.write_graphml(graphml_dag, dag_basename + '.graphml')
