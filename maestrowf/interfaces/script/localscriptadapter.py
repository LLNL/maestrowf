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

from maestrowf.abstracts.interfaces import ScriptAdapter

LOGGER = logging.getLogger(__name__)


class LocalScriptAdapter(ScriptAdapter):
    """
    A ScriptAdapter class for interfacing with the SLURM cluster scheduler.
    """
    def __init__(self, **kwargs):
        """
        Initialize an instance of the LocalScriptAdapter.

        The LocalScriptAdapter is the adapter that is used for

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        super(LocalScriptAdapter, self).__init__()

        # NOTE: Host doesn't seem to matter for SLURM. sbatch assumes that the
        # current host is where submission occurs.
        self._exec = kwargs.pop("shell", "#!/bin/bash")

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
        written script for run["cmd"], and the path to the script written for
        run["restart"] (if it exists).
        """
        cmd = step.run["cmd"]
        restart = step.run["restart"]
        to_be_scheduled = False

        fname = "{}.sh".format(step.name)
        script_path = os.path.join(ws_path, fname)
        with open(script_path, "w") as script:
            script.write(self._exec)
            _ = "\n\n{}\n".format(cmd)
            script.write(_)

        if restart:
            rname = "{}.restart.sh".format(step.name)
            restart_path = os.path.join(ws_path, rname)

            with open(restart_path, "w") as script:
                script.write(self._exec)
                _ = "\n\n{}\n".format(restart)
                script.write(_)
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path
