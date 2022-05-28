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

"""Slurm Scheduler interface implementation."""
import getpass
import logging
import os
import re
# In order to support Python2.7, we need to catch the import error.
try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from maestrowf.abstracts.interfaces import SchedulerScriptAdapter
from maestrowf.abstracts.enums import JobStatusCode, State, SubmissionCode, \
    CancelCode
from maestrowf.interfaces.script import CancellationRecord, SubmissionRecord
from maestrowf.utils import start_process

LOGGER = logging.getLogger(__name__)


class SlurmScriptAdapter(SchedulerScriptAdapter):
    """A ScriptAdapter class for interfacing with the SLURM scheduler."""

    key = "slurm"

    def __init__(self, **kwargs):
        """
        Initialize an instance of the SlurmScriptAdapter.

        The SlurmScriptAdapter is this package's interface to the Slurm
        scheduler. This adapter constructs Slurm scripts for a StudyStep based
        on user set defaults and local settings present in each step.

        The expected keyword arguments that are expected when the Slurm adapter
        is instantiated are as follows:
        - host: The cluster to execute scripts on.
        - bank: The account to charge computing time to.
        - queue: Scheduler queue scripts should be submitted to.
        - nodes: The number of compute nodes to be reserved for computing.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        super(SlurmScriptAdapter, self).__init__(**kwargs)

        # NOTE: Host doesn't seem to matter for SLURM. sbatch assumes that the
        # current host is where submission occurs.
        self.add_batch_parameter("host", kwargs.pop("host"))
        self.add_batch_parameter("bank", kwargs.pop("bank"))
        self.add_batch_parameter("queue", kwargs.pop("queue"))
        self.add_batch_parameter("nodes", kwargs.pop("nodes", "1"))
        self.add_batch_parameter("reservation", kwargs.pop("reservation", ""))

        # Check for procs separately, as we don't want it in the header if it's
        # not present.
        procs = kwargs.get("procs", None)
        if procs:
            self.add_batch_parameter("procs", procs)

        self._header = {
            "nodes": "#SBATCH --nodes={nodes}",
            "queue": "#SBATCH --partition={queue}",
            "bank": "#SBATCH --account={bank}",
            "walltime": "#SBATCH --time={walltime}",
            "job-name":
                "#SBATCH --job-name=\"{job-name}\"\n"
                "#SBATCH --output=\"{job-name}.out\"\n"
                "#SBATCH --error=\"{job-name}.err\"",
            "comment": "#SBATCH --comment \"{comment}\"",
            "reservation": "#SBATCH --reservation=\"{reservation}\"",
            "gpus": "#SBATCH --gres=gpu:{gpus}"
        }

        self._cmd_flags = {
            "cmd": "srun",
            "depends": "--dependency",
            "ntasks": "-n",
            "nodes": "-N",
            "cores per task": "-c",
        }
        self._unsupported = set(["cmd", "depends", "ntasks", "nodes"])

    def get_header(self, step):
        """
        Generate the header present at the top of Slurm execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
            the parameter step.
        """
        resources = ChainMap(step.run, self._batch)
        resources["job-name"] = step.name.replace(" ", "_")
        resources["comment"] = step.description.replace("\n", " ")

        modified_header = ["#!{}".format(self._exec)]
        for key, value in self._header.items():
            if key not in resources:
                continue

            if resources[key]:
                modified_header.append(value.format(**resources))

        if "procs" in self._batch:
            modified_header.append(
                "#SBATCH --ntasks={}".format(resources["procs"])
            )

        exclusive = resources.get("exclusive", False)
        if exclusive:
            modified_header.append("#SBATCH --exclusive")

        return "\n".join(modified_header)

    def get_parallelize_command(self, procs, nodes=None, **kwargs):
        """
        Generate the SLURM parallelization segement of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
            (default = 1).
        :returns: A string of the parallelize command configured using nodes
            and procs.
        """
        args = [
            # SLURM srun command
            self._cmd_flags["cmd"],
            # Processors segment
            self._cmd_flags["ntasks"],
            str(procs)
        ]

        if nodes:
            args += [
                self._cmd_flags["nodes"],
                str(nodes),
            ]

        supported = set(kwargs.keys()) - self._unsupported
        for key in supported:
            value = kwargs.get(key)
            if key not in self._cmd_flags:
                LOGGER.warning("'%s' is not supported -- ommitted.", key)
                continue
            if value:
                args += [
                    self._cmd_flags[key],
                    "{}".format(str(value))
                ]

        return " ".join(args)

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
        # Leading command is 'sbatch'
        cmd = ["sbatch"]
        # Check and see if we should be submitting into a reservation.
        if "reservation" in self._batch:
            if self._batch["reservation"]:
                cmd += ["--reservation", self._batch["reservation"]]

        # Append the script path and working directory.
        cmd += ["-D", cwd, path]
        cmd = " ".join(cmd)

        LOGGER.debug("cwd = %s", cwd)
        LOGGER.debug("Command to execute: %s", cmd)
        p = start_process(cmd, cwd=cwd, env=env)
        output, err = p.communicate()
        retcode = p.wait()

        # TODO: We need to check for dependencies here. The sbatch is where
        # dependent batch jobs are specified. If we're trying to launch
        # everything at once then that should happen here.

        if retcode == 0:
            LOGGER.info("Submission returned status OK.")
            jid = re.search('[0-9]+', output).group(0)
            return SubmissionRecord(SubmissionCode.OK, retcode, jid)
        else:
            LOGGER.warning(
                "Submission returned an error (see next line).\n%s", err)
            return SubmissionRecord(SubmissionCode.ERROR, retcode)

    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        This method uses the scontrol show job <jobid> command and does a
        regex search for job information.

        :param joblist: A list of job identifiers to be queried.
        :returns: The return code of the status query, and a dictionary of job
            identifiers to their status.
        """
        # TODO: This method needs to be updated to use sacct.
        # squeue options:
        # -u = username to search queues for.
        # -t = list of job states to search for. 'all' for all states.
        cmd = "squeue -u $USER -t all"
        p = start_process(cmd)
        output, err = p.communicate()
        retcode = p.wait()

        status = {}
        for jobid in joblist:
            LOGGER.debug("Looking for jobid %s", jobid)
            status[jobid] = None

        if retcode == 0:
            for job in output.split("\n")[1:]:
                LOGGER.debug("Job Entry: %s", job)
                # The squeue command output is split with the following indices
                # used for specific information:
                # 0 - Job Identifier
                # 1 - Queue
                # 2 - Job name
                # 3 - User
                # 4 - State [Passed to _state]
                # 5 - Current Execution Time
                # 6 - Assigned Node Count
                # 7 - Hostname and assigned node identifier list
                job_split = re.split(r"\s+", job)
                state_index = 4
                jobid_index = 0
                if job_split[0] == "":
                    LOGGER.debug("Removing blank entry from head of status.")
                    job_split = job_split[1:]

                LOGGER.debug("Entry split: %s", job_split)
                if not job_split:
                    LOGGER.debug("Continuing...")
                    continue

                if job_split[jobid_index] in status:
                    LOGGER.debug("ID Found. %s -- %s", job_split[state_index],
                                 self._state(job_split[state_index]))
                    status[job_split[jobid_index]] = \
                        self._state(job_split[state_index])

            return JobStatusCode.OK, status
        elif retcode == 1:
            LOGGER.warning("User '%s' has no jobs executing. Returning.",
                           getpass.getuser())
            return JobStatusCode.NOJOBS, status
        else:
            LOGGER.error("Error code '%s' seen. Unexpected behavior "
                         "encountered.")
            return JobStatusCode.ERROR, status

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
        """
        # If we don't have any jobs to check, just return status OK.
        if not joblist:
            return CancellationRecord(CancelCode.OK, 0)

        cmd = "scancel --quiet {}".format(" ".join(joblist))
        p = start_process(cmd)
        output, err = p.communicate()
        retcode = p.wait()

        if retcode == 0:
            _record = CancellationRecord(CancelCode.OK, retcode)
        else:
            LOGGER.error("Error code '%s' seen. Unexpected behavior "
                         "encountered.")
            _record = CancellationRecord(CancelCode.ERROR, retcode)

        return _record

    def _state(self, slurm_state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param slurm_state: String representation of scheduler job status.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        LOGGER.debug("Received SLURM State -- %s", slurm_state)
        if slurm_state == "R":
            return State.RUNNING
        elif slurm_state == "PD":
            return State.PENDING
        elif slurm_state == "CG":
            return State.FINISHING
        elif slurm_state == "CD":
            return State.FINISHED
        elif slurm_state == "NF":
            return State.HWFAILURE
        elif slurm_state == "TO":
            return State.TIMEDOUT
        elif slurm_state == "ST" or slurm_state == "F":
            return State.FAILED
        elif slurm_state == "CA":
            return State.CANCELLED
        else:
            return State.UNKNOWN

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
            written script for run["cmd"], and the path to the script written
            for run["restart"] (if it exists).
        """
        to_be_scheduled, cmd, restart = self.get_scheduler_command(step)

        fname = "{}.slurm.sh".format(step.name)
        script_path = os.path.join(ws_path, fname)

        if to_be_scheduled:
            header = self.get_header(step)
        else:
            header = "#!{}".format(self._exec)

        form_cmd = "{0}\n\n{1}\n"
        with open(script_path, "w") as script:
            script.write(form_cmd.format(header, cmd))

        if restart:
            rname = "{}.restart.slurm.sh".format(step.name)
            restart_path = os.path.join(ws_path, rname)

            with open(restart_path, "w") as script:
                script.write(form_cmd.format(header, restart))
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path
