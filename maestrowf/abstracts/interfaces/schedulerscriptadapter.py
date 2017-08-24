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

"""Abstract Cluster Interfaces defining the API for interacting with queues."""
from abc import ABCMeta, abstractmethod
import logging
import re
import six

from maestrowf.abstracts.interfaces.scriptadapter import ScriptAdapter

LOGGER = logging.getLogger(__name__)


@six.add_metaclass(ABCMeta)
class SchedulerScriptAdapter(ScriptAdapter):
    """
    Abstract class representing the interface for scheduling scripts.

    This class handles both the construction of scripts (as required by the
    ScriptAdapter base class) but also includes the necessary methods for
    constructing parallel commands. The adapter will substitute parallelized
    commands but also defines how to schedule and check job status.
    """
    # The var tag to look for to replace for parallelized commands.
    launcher_var = "$(LAUNCHER)"
    # Allocation regex and compilation
    alloc_regex = re.compile(
        re.escape(launcher_var) +
        r"\[(?P<nodes>[0-9]+),\s*(?P<procs>[0-9]+)\]"
    )

    def __init__(self):
        """
        Initialize an empty ScriptAdapter object.
        """
        # NOTE: The _batch member should be used to store persistent batching
        # parameters. The entries in this dictionary are meant to capture the
        # the base settings for submission to a batch. This member variables
        # should never be used publicallly outside of an instance.
        self._batch = {}

    def add_batch_parameter(self, name, value):
        """
        Add a parameter to the ScriptAdapter instance.

        :param name: String name of the parameter that's being added.
        :param value: Value associated with the parameter name (should have a
        str method).
        """
        self._batch[name] = value

    @abstractmethod
    def get_header(self, step):
        """
        Generate the header present at the top of execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
        the parameter step.
        """
        pass

    @abstractmethod
    def get_parallelize_command(self, procs, nodes=1):
        """
        Generate the parallelization segement of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
        (default = 1).
        :returns: A string of the parallelize command configured using nodes
        and procs.
        """
        pass

    def _substitute_parallel_command(self, step_cmd, nodes, procs):
        """
        Substitute parallelized segements into a specified command.

        :param step_cmd: Command string to parallelize.
        :param nodes: Total number of requested nodes.
        :param procs: Total number of requested processors.
        :returns: The new command with all allocations substituted.
        """
        err_msg = "{} attempting to allocate {} {} for a parallel call with" \
                  " a maximum allocation of {}"

        # We have three things that can happen.
        # 1. We are partitioning the allocation into smaller chunks.
        # We need to check for the launcher tag with specified values.
        search = list(re.finditer(self.alloc_regex, step_cmd))
        cmd = step_cmd
        if search:
            LOGGER.debug("Allocation setup found. cmd=%s", step_cmd)
            for match in search:
                # For each regex match that we found do:
                # Collect the nodes and procs in the launch allocation.
                alloc_nodes = match.group("nodes")
                alloc_procs = match.group("procs")
                # Compare the allocation to step allocation.
                if int(alloc_nodes) > nodes:
                    msg = err_msg.format(
                        match.group(),
                        alloc_nodes,
                        "nodes",
                        nodes
                    )
                    LOGGER.error(msg)
                    raise ValueError(msg)
                if int(alloc_procs) > procs:
                    msg = err_msg.format(
                        match.group(),
                        alloc_procs,
                        "procs",
                        procs
                    )
                    LOGGER.error(msg)
                    raise ValueError(msg)
                # Compute the parallel command.
                parallel_cmd = self.get_parallelize_command(
                    alloc_procs,
                    alloc_nodes
                )
                # Substitute the match with the parallel command.
                cmd = cmd.replace(match.group(), parallel_cmd)
            # Return the new command.
            return cmd
        # 2. If not allocating,then sub in for launcher if it exists.
        parallel_cmd = self.get_parallelize_command(procs, nodes)
        search = list(re.finditer(re.escape(self.launcher_var), step_cmd))
        if search:
            LOGGER.debug("Launcher token set up found. cmd=%s", step_cmd)
            if len(search) == 1:
                cmd = step_cmd.replace(search[0].group(), parallel_cmd)
            else:
                msg = "'{}' command has more than one instance of {}." \
                    .format(step_cmd, self.launcher_var)
                LOGGER.error(msg)
                raise ValueError(msg)
            return cmd
        # 3. Otherwise, just prepend the command to the front.
        LOGGER.debug("Prepending parallel command. cmd=%s", step_cmd)
        return " ".join([parallel_cmd, step_cmd])

    def get_scheduler_command(self, step):
        """
        Generate the full parallelized command for use in a batch script.

        :param step: A StudyStep instance.
        :returns:
            1. A Boolean value - True if command is to be scheduled, False
            otherwise.
            2. A string representing the parallelized batch command for the
            specified step command.
            3. A string representing the parallelized batch command for the
            specified step restart command.
        """
        # We should never get a study step that doesn't have a run entry; but
        # better to be safe.
        if not step.run:
            msg = "Malformed StudyStep. A StudyStep requires a run entry."
            LOGGER.error(msg)
            raise ValueError(msg)

        # If the user is requesting nodes, we need to request the nodes and
        # set up the command with scheduling.
        step_nodes = step.run.get("nodes", 1)
        step_procs = step.run.get("procs")
        if step_nodes or step_procs:
            to_be_scheduled = True
            cmd = self._substitute_parallel_command(
                step.run["cmd"],
                step_nodes,
                step_procs
            )
            LOGGER.debug("Scheduling command: %s", cmd)

            # Also check for the restart command and parallelize it too.
            restart = ""
            if step.run["restart"]:
                restart = self._substitute_parallel_command(
                    step.run["restart"],
                    step_nodes,
                    step_procs
                )
                LOGGER.debug("Restart command: %s", cmd)
            LOGGER.info("Scheduling workflow step '%s'.", step.name)
        # Otherwise, just return the command. It doesn't need scheduling.
        else:
            LOGGER.info("Running workflow step '%s' locally.", step.name)
            to_be_scheduled = False
            cmd = step.run["cmd"]
            restart = step.run["restart"]

        return to_be_scheduled, cmd, restart

    @abstractmethod
    def _write_script(self, ws_path, step):
        """
        Write a script to the workspace of a workflow step.

        The job_map optional parameter is a map of workflow step names to job
        identifiers. This parameter so far is only planned to be used when a
        study is configured to be launched in one go (more or less a script
        chain using a scheduler's dependency setting). The functionality of
        the parameter may change depending on both future intended use and
        derived classes.

        :param ws_path: Path to the workspace directory of the step.
        :param step: An instance of a StudyStep.
        :returns: Boolean value (True if the workflow step is to be scheduled,
        False otherwise) and the path to the written script.
        """
        pass

    @abstractmethod
    def _state(self, job_state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param job_state: String representation of scheduler job status.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        pass
