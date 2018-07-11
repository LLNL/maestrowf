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
"""A centralized module for parallelizing commands."""
import logging
import re

from maestrowf.interfaces.mpi import ParallelizerFactory

LOGGER = logging.getLogger(__name__)


class CommandParallelizer(object):
    """Abstract class representing the interface for command parallelizing."""

    # The var tag to look for to replace for parallelized commands.
    launcher_var = "$(LAUNCHER)"
    # Allocation regex and compilation
    # Keeping this one here for legacy.
    launcher_regex = re.compile(
        re.escape(launcher_var) + r"(\[(?P<alloc>.*)\])?")

    # We can have multiple requested submission properties.
    task_alloc = re.compile(r"(?P<procs>[0-9]+)t")
    # Just allocate based on nodes.
    node_alloc = re.compile(r"(?P<nodes>[0-9]+)n")
    # Find the an mpi specification.
    mpi_spec = re.compile(r"(?P<mpi>[aA-zZ]{2,})")

    @classmethod
    def parallelize(self, cmd, resources, default_mpi):
        """
        Generate the parallelization segement of the command line.

        :param cmd: Command string to substitute parallel command into.
        :param resources: Dict of resources to be used by parallel commands.
        :param default_mpi: Name of the default parallelization MPI binary.
        :returns: A string of the parallelize command configured using the
        specified resources.
        """
        # Find all matches for the launcher pattern in the command.
        matches = re.finditer(self.launcher_regex, cmd)
        LOGGER.debug("Found %d matches:\n%s", len(matches), cmd)
        # We need to keep track of specific resources each match uses.
        cmd_per_mpi = {default_mpi: {}}

        for match in matches:
            LOGGER.debug("Parallel command: %s", match.group())
            # For each match,
            # Find the allocation group if it exists.
            _alloc = match.group("alloc")
            # If we find alloc, then we need to parse further.
            if _alloc:
                LOGGER.debug("Sub-allocation detected (%s)", _alloc)
                # Break down the allocation if one is specified.
                mpi = re.search(self.mpi_spec, _alloc)
                task = re.search(self.task_alloc, _alloc)
                node = re.search(self.node_alloc, _alloc)
                # Construct the suballocation dictionary.
                _ = {
                    "nodes": node.group("nodes") if node else None,
                    "tasks": task.group("tasks") if task else None,
                }
                # If a custom MPI is specified, mark it under the specified
                # version.
                if mpi:
                    LOGGER.debug("Custom MPI specified (%s)", mpi.group("mpi"))
                    cmd_per_mpi[mpi.group("mpi")][match.group()] = _
                else:
                    LOGGER.debug("Default MPI used (%s)", default_mpi)
                    # Otherwise, just the default.
                    cmd_per_mpi[default_mpi][match.group()] = _
            else:
                LOGGER.debug("No allocation detected. Using %s", default_mpi)
                _ = {
                    "nodes": resources.get("nodes", None),
                    "tasks": resources.get("tasks"),
                }
                cmd_per_mpi[default_mpi][match.group()] = _

        for key, cmds in cmd_per_mpi.items():
            # parallelizer = ParallelizerFactory.get_parallelizer(key)
            # TODO: We need to use the parallelizer here to sub into our cmd.
            pass
