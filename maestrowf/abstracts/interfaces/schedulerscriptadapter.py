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
import six

from maestrowf.interfaces import CommandParallelizer
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

    def __init__(self):
        """Initialize an empty ScriptAdapter object."""
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

            # TODO: We could introduce the new format for the specification.
            # The new resource specification would make it so that all resource
            # definition occurs in one place that could simply be passed to
            # the 'parallelize' method.
            resources = {
                "nodes": _nodes,
                "tasks": _procs,
                "gpus": step.run.get("gpus", 0),
                "cores per task": step.run.get("cores per task", None),
            }
            cmd = CommandParallelizer.parallelize(
                step.run["cmd"], resources, self._default_mpi)
            LOGGER.debug("Scheduling command: %s", cmd)

            # Also check for the restart command and parallelize it too.
            restart = ""
            if step.run["restart"]:
                restart = CommandParallelizer.parallelize(
                    step.run["restart"], resources, self._default_mpi)
                LOGGER.debug("Restart command: %s", restart)
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
