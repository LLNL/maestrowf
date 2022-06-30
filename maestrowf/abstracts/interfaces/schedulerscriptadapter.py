
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
    # Keeping this one here for legacy.
    launcher_regex = re.compile(
        re.escape(launcher_var) + r"\[(?P<alloc>.*)\]")

    # We can have multiple requested submission properties.
    # Legacy allocation of nodes and procs.
    legacy_alloc = r"(?P<nodes>[0-9]+),\s*(?P<procs>[0-9]+)"
    # Just allocate based on tasks.
    task_alloc = r"(?P<procs>[0-9]+)p"
    # Just allocate based on nodes.
    node_alloc = r"(?P<nodes>[0-9]+)n"

    def __init__(self, **kwargs):
        """
        Initialize an empty ScriptAdapter object.

        :param kwargs: Key-value dictionary of arguments.

        Currently we only support the "shell" keyword.
        """
        # NOTE: The _batch member should be used to store persistent batching
        # parameters. The entries in this dictionary are meant to capture the
        # the base settings for submission to a batch. This member variables
        # should never be used publicly outside of an instance.

        # Call super to set self._exec
        super(SchedulerScriptAdapter, self).__init__(**kwargs)
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
    def get_parallelize_command(self, procs, nodes, **kwargs):
        """
        Generate the parallelization segment of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
            (default = 1).
        :returns: A string of the parallelize command configured using nodes
            and procs.
        """
        pass

    def _substitute_parallel_command(self, step_cmd, **kwargs):
        """
        Substitute parallelized segments into a specified command.

        :param step_cmd: Command string to parallelize.
        :param nodes: Total number of requested nodes.
        :param procs: Total number of requested processors.
        :returns: The new command with all allocations substituted.
        """
        err_msg = "{} attempting to allocate {} {} for a parallel call with" \
                  " a maximum allocation of {}"

        nodes = kwargs.get("nodes")
        procs = kwargs.get("procs")
        addl_args = dict(kwargs)
        addl_args.pop("nodes")
        addl_args.pop("procs")

        LOGGER.debug("nodes=%s; procs=%s", nodes, procs)
        # See if the command contains a launcher token in it.
        alloc_search = list(re.finditer(self.launcher_regex, step_cmd))
        if alloc_search:
            # If we find that launcher nomenclature.
            total_nodes = 0     # Total nodes we've allocated so far.
            total_procs = 0     # Total processors we've allocated so far.
            cmd = step_cmd      # The step command we'll substitute into.
            for match in alloc_search:
                LOGGER.debug("Found a match: %s", match.group())
                _nodes = None
                _procs = None
                # Look for the allocation information in the match.
                _alloc = match.group("alloc")
                # Search for the legacy format.
                _legacy = re.search(self.legacy_alloc, _alloc)
                if _legacy:
                    # nodes, procs legacy notation.
                    _ = _alloc.split(",")
                    _nodes = _[0]
                    _procs = _[1]
                    LOGGER.debug(
                        "Legacy setup detected. (nodes=%s, procs=%s)",
                        _nodes,
                        _procs
                    )
                else:
                    # We're dealing with the new style.
                    # Make sure we only have at most one proc and node
                    # allocation specified.
                    if _alloc.count("p") > 1 or _alloc.count("n") > 1:
                        msg = "cmd: {}\n Invalid allocations specified ({})." \
                              " Number of nodes and/or procs must only be " \
                              "specified once." \
                              .format(step_cmd, _alloc)
                        LOGGER.error(msg)
                        raise ValueError(msg)

                    if _alloc.count("p") < 1:
                        msg = "cmd: {}\n Invalid allocations specified ({})." \
                              " Processors/tasks must be specified." \
                              .format(step_cmd, _alloc)
                        LOGGER.error(msg)
                        raise ValueError(msg)

                    _nodes = re.search(self.node_alloc, _alloc)
                    if _nodes:
                        _nodes = _nodes.group("nodes")
                    _procs = re.search(self.task_alloc, _alloc)
                    if _procs:
                        _procs = _procs.group("procs")

                    LOGGER.debug(
                        "New setup detected. (nodes=%s, procs=%s)",
                        _nodes,
                        _procs
                    )

                msg = []
                # Check that the requested nodes are within range.
                if _nodes:
                    _ = int(_nodes)
                    total_nodes += _
                    if _ > nodes:
                        msg.append(
                            err_msg.format(
                                match.group(), _nodes, "nodes", nodes
                            )
                        )
                # Check that the requested processors is within range.
                if _procs:
                    _ = int(_procs)
                    total_procs += _
                    if _ > procs:
                        msg.append(
                            err_msg.format(
                                match.group(), _procs, "procs", procs
                            )
                        )
                # If we have constructed a message, raise an exception.
                if msg:
                    LOGGER.error(msg)
                    raise ValueError(msg)

                pcmd = self.get_parallelize_command(
                    _procs, _nodes, **addl_args
                )
                cmd = cmd.replace(match.group(), pcmd)

            # Verify that the total nodes/procs used is within maximum.
            if total_procs > procs:
                msg = "Total processors ({}) requested exceeds the " \
                      "maximum requested ({})".format(total_procs, procs)
                LOGGER.error(msg)
                raise ValueError(msg)

            if nodes and total_nodes > nodes:
                msg = "Total nodes ({}) requested exceeds the " \
                      "maximum requested ({})".format(total_nodes, nodes)
                LOGGER.error(msg)
                raise ValueError(msg)

            return cmd
        else:
            # 3. Two smaller cases here. If we see the launcher token WITHOUT
            # any parameters, replace it there with full nodes and procs.
            # Otherwise, just return the command. A user may simply want to run
            # an unparallelized code in a submission.
            pcmd = self.get_parallelize_command(procs, nodes, **addl_args)
            # Catch the case where the launcher token appears on its own
            if self.launcher_var in step_cmd:
                LOGGER.debug(
                    "'%s' found in cmd. Substituting", self.launcher_var)
                return step_cmd.replace(self.launcher_var, pcmd)
            else:
                LOGGER.debug("The command did not specify an MPI command.")
                return step_cmd

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
        _nodes = step.run.get("nodes", 0)
        _procs = step.run.get("procs", 0)
        if _nodes or _procs:
            to_be_scheduled = True
            cmd = self._substitute_parallel_command(
                step.run["cmd"],
                **step.run
            )
            LOGGER.debug("Scheduling command: %s", cmd)

            # Also check for the restart command and parallelize it too.
            restart = ""
            if step.run["restart"]:
                restart = self._substitute_parallel_command(
                    step.run["restart"],
                    **step.run
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

    def get_priority(self, priority):
        """
        Map a fixed enumeration or floating point priority to a batch priority.

        :param priority: Float or StepPriority enum representing priorty.
        :returns: A string, integer, or float value representing the mapped
        priority to the batch scheduler.
        """
        raise NotImplementedError()
