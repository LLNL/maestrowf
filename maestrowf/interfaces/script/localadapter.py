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

"""Local script interface implementation."""
import getpass
import logging
import os
import re
from subprocess import PIPE, Popen

from maestrowf.abstracts import ScriptAdapter
from maestrowf.datastructures.core import State
from maestrowf.abstracts.interfaces import JobStatusCode, SubmissionCode

LOGGER = logging.getLogger(__name__)


class LocalScriptAdapter(ScriptAdapter):
    """
    A ScriptAdapter class for executing on a local machine.
    """
    def __init__(self, **kwargs):
        """
        Initialize an instance of the LocalScriptAdapter.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        super(LocalScriptAdapter, self).__init__()
        self._exec = kwargs.pop("header", "#!/bin/bash")

    def get_header(self, step):
        """
        Generate the header present at the top of Slurm execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
        the parameter step.
        """
        return self._exec

    def get_parallelize_command(self, procs, nodes=1):
        """
        Generate the SLURM parallelization segement of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
        (default = 1).
        :returns: A string of the parallelize command configured using nodes
        and procs.
        """
        return ""

    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Submit a script to the Slurm scheduler.

        :param step: The StudyStep instance this submission is based on.
        :param path: Local path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A dictionary mapping step names to their job
        identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return status of the submission command and job
        identiifer.
        """
        LOGGER.debug("Script to execute: %s", path)
        p = Popen(path, shell=True, stdout=PIPE, stderr=PIPE, cwd=cwd, env=env)
        output, err = p.communicate()
        retcode = p.wait()

        # TODO: We need to check for dependencies here. The sbatch is where
        # dependent batch jobs are specified. If we're trying to launch
        # everything at once then that should happen here.

        if retcode == 0:
            LOGGER.info("Submission returned status OK.")
            return SubmissionCode.OK, re.search('[0-9]+', output).group(0)
        else:
            LOGGER.warning("Submission returned an error.")
            return SubmissionCode.ERROR, -1

    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        This method uses the scontrol show job <jobid> command and does a
        regex search for job information.

        :param joblist: A list of job identifiers to be queried.
        :returns: The return code of the status query, and a dictionary of job
        identifiers to their status.
        """
        pass

    def _state(self, state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param state: String representation of scheduler job status.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        pass

    def _write_script(self, ws_path, step):
        """
        Write a Slurm script to the workspace of a workflow step.

        The job_map optional parameter is a map of workflow step names to job
        identifiers. This parameter so far is only planned to be used when a
        study is configured to be launched in one go (more or less a script
        chain using a scheduler's dependency setting). The functionality of
        the parameter may change depending on both future intended use.

        :param ws_path: Path to the workspace directory of the step.
        :param step: An instance of a StudyStep.
        :returns: Boolean value (True if to be scheduled), the path to the
        written script for run["cmd"], and the path to the script written for
        run["restart"] (if it exists).
        """
        pass
