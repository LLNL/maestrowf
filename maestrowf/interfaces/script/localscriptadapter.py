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

"""Local interface implementation."""
import logging
import os

from maestrowf.abstracts.enums import JobStatusCode, SubmissionCode, \
    CancelCode
from maestrowf.interfaces.script import CancellationRecord, SubmissionRecord
from maestrowf.abstracts.interfaces import ScriptAdapter
from maestrowf.utils import start_process

LOGGER = logging.getLogger(__name__)


class LocalScriptAdapter(ScriptAdapter):
    """A ScriptAdapter class for interfacing for local execution."""

    key = "local"

    def __init__(self, **kwargs):
        """
        Initialize an instance of the LocalScriptAdapter.

        The LocalScriptAdapter is the adapter that is used for workflows that
        will execute on the user's machine. The only configurable aspect to
        this adapter is the shell that scripts are executed in.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        LOGGER.debug("kwargs\n--------------------------\n%s", kwargs)
        super(LocalScriptAdapter, self).__init__(**kwargs)
        self._extension = ".sh"

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
        :returns: False (will not be scheduled), the path to the
            written script for run["cmd"], and the path to the script written
            for run["restart"] (if it exists).
        """
        cmd = step.run["cmd"]
        restart = step.run["restart"]
        to_be_scheduled = False

        fname = "{}.sh".format(step.name)
        script_path = os.path.join(ws_path, fname)
        with open(script_path, "w") as script:
            script.write("#!{0}\n\n{1}\n".format(self._exec, cmd))

        if restart:
            rname = "{}.restart.sh".format(step.name)
            restart_path = os.path.join(ws_path, rname)

            with open(restart_path, "w") as script:
                script.write("#!{0}\n\n{1}\n".format(self._exec, restart))
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path

    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        :param joblist: A list of job identifiers to be queried.
        :returns: The return code of the status query, and a dictionary of job
            identifiers to their status.
        """
        return JobStatusCode.NOJOBS, {}

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
        """
        return CancellationRecord(CancelCode.OK, 0)

    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Execute the step locally.

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
        LOGGER.debug("cwd = %s", cwd)
        LOGGER.debug("Script to execute: %s", path)
        p = start_process(path, shell=False, cwd=cwd, env=env)
        pid = p.pid
        output, err = p.communicate()
        retcode = p.wait()

        o_path = os.path.join(cwd, "{}.{}.out".format(step.name, pid))
        e_path = os.path.join(cwd, "{}.{}.err".format(step.name, pid))

        with open(o_path, "w") as out:
            out.write(output)

        with open(e_path, "w") as out:
            out.write(err)

        if retcode == 0:
            LOGGER.info("Execution returned status OK.")
            return SubmissionRecord(SubmissionCode.OK, retcode, pid)
        else:
            LOGGER.warning("Execution returned an error: %s", str(err))
            _record = SubmissionRecord(SubmissionCode.ERROR, retcode, pid)
            _record.add_info("stderr", str(err))
            return _record

    @property
    def extension(self):
        return self._extension
