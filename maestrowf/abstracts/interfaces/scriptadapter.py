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
import os
import six
import stat

LOGGER = logging.getLogger(__name__)


@six.add_metaclass(ABCMeta)
class ScriptAdapter(object):
    """
    Abstract class representing the interface for constructing scripts.

    The ScriptAdapter abstract class is meant to provide a consistent high
    level interface to generate scripts automatically based on an ExecutionDAG.
    Adapters as a whole should only interface with the ExecutionDAG because it
    is ultimately the DAG that manages the state of tasks. Adapters attempt to
    bridge the 'how' in an abstract way such that the interface is refined to
    methods such as:
        - Generating a script with the proper syntax to submit.
        - Submitting a script using the proper command.
        - Checking job status.
    """

    # The var tag to look for to replace for parallelized commands.
    launcher_var = "$(LAUNCHER)"

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
    def get_parallelize_command(self, step):
        """
        Generate the parallelization segement of the command line.

        :param step: A StudyStep instance.
        :returns: A string of the parallelize command configured using step.
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
        step_nodes = step.run.get("nodes")
        step_procs = step.run.get("procs")
        if step_nodes or step_procs:
            to_be_scheduled = True
            # Get the parallelized command.
            parallel_cmd = self.get_parallelize_command(step)
            # If we pick up the $(LAUNCHER) token, replace it.
            if self.launcher_var in step.run["cmd"]:
                cmd = step.run["cmd"].replace(self.launcher_var, parallel_cmd)
            else:
                cmd = " ".join([parallel_cmd, step.run["cmd"]])

            # Also check for the restart command and parallelize it too.
            restart = ""
            if step.run["restart"]:
                if self.launcher_var in step.run["restart"]:
                    restart = step.run["restart"] \
                            .replace(self.launcher_var, parallel_cmd)
                else:
                    restart = " ".join([parallel_cmd, step.run["restart"]])

                    LOGGER.info("Scheduling workflow step '%s'.", step.name)
        # Otherwise, just return the command. It doesn't need scheduling.
        else:
            LOGGER.info("Running workflow step '%s' locally.", step.name)
            to_be_scheduled = False
            cmd = step.run["cmd"]
            restart = step.run["restart"]

        return to_be_scheduled, cmd, restart

    @abstractmethod
    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        :param joblist: A list of job identifiers to be queried.
        :returns: The return code of the status query, and a dictionary of job
        identifiers to their status.
        """
        pass

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

    def write_script(self, ws_path, step):
        """
        Generate the script for the specified StudyStep.

        :param ws_path: Workspace path for the step.
        :param step: An instance of a StudyStep class.
        :returns: A tuple containing a boolean set to True if step should be
        scheduled (False otherwise), path to the generate script, and path
        to the generated restart script (None if step cannot be restarted).
        """
        to_be_scheduled, script_path, restart_path = \
            self._write_script(ws_path, step)
        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IXUSR)

        if restart_path:
            st = os.stat(restart_path)
            os.chmod(restart_path, st.st_mode | stat.S_IXUSR)

        return to_be_scheduled, script_path, restart_path

    @abstractmethod
    def _state(self, job_state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param job_state: String representation of scheduler job status.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        pass

    @abstractmethod
    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Submit a script to the scheduler.

        If cwd is specified, the submit method will operate outside of the path
        specified by the 'cwd' parameter.
        If env is specified, the submit method will set the environment
        variables for submission to the specified values. The 'env' parameter
        should be a dictionary of environment variables.

        :param step: An instance of a StudyStep.
        :param path: Path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A map of workflow step names to their job identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return code of the submission command and job identiifer.
        """
        pass
