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

"""Abstract Script Interfaces for generating scripts."""
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
    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
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
