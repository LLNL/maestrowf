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

"""LSF Scheduler interface implementation."""
import getpass
import logging
from math import ceil
import os
import re
from subprocess import PIPE, Popen

from maestrowf.abstracts.interfaces import SchedulerScriptAdapter
from maestrowf.abstracts.enums import CancelCode, JobStatusCode, State, \
    SubmissionCode
from maestrowf.interfaces.script import CancellationRecord, SubmissionRecord


LOGGER = logging.getLogger(__name__)


class LSFScriptAdapter(SchedulerScriptAdapter):
    """A ScriptAdapter class for interfacing with the LSF cluster scheduler."""

    NOJOB_REGEX = re.compile(r"^No\s")
    key = "lsf"

    def __init__(self, **kwargs):
        """
        Initialize an instance of the SlurmScriptAdapter.

        The SlurmScriptAdapter is this package's interface to the Slurm
        scheduler. This adapter constructs Slurm scripts for a StudyStep based
        on user set defaults and local settings present in each step.

        The expected keyword arguments that are expected when the Slurm adapter
        is instantiated are as follows:
        * host: The cluster to execute scripts on.
        * bank: The account to charge computing time to.
        * queue: Scheduler queue scripts should be submitted to.
        * tasks: The number of compute nodes to be reserved for computing.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        super(LSFScriptAdapter, self).__init__()

        # NOTE: Host doesn't seem to matter for LSF
        self.add_batch_parameter("host", kwargs.pop("host"))
        self.add_batch_parameter("bank", kwargs.pop("bank"))
        self.add_batch_parameter("queue", kwargs.pop("queue"))
        self.add_batch_parameter("nodes", kwargs.pop("nodes", "1"))

        reservation = kwargs.get("reservation", None)
        if reservation:
            self.add_batch_parameter("reservation", reservation)

        self._header = {
            "nodes": "#BSUB -nnodes {nodes}",
            "queue": "#BSUB -q {queue}",
            "bank": "#BSUB -G {bank}",
            "walltime": "#BSUB -W {walltime}",
            "job-name": "#BSUB -J {job-name}",
            "output": "#BSUB -o {output}",
            "reservation": "#BSUB -U {reservation}",
            "error": "#BSUB -e {error}",
        }

        self._cmd_flags = {
            "cmd":          "jsrun",
            "rs per node":  "-r",
            "ntasks":       "--nrs",
            "tasks per rs": "-a",
            "gpus":         "-g",
            "cpus per rs":  "-c",
            "reservation":  "-J",
            "bind":         "-b",
            "bind gpus":    "-B",
        }

        self._extension = "lsf.sh"

    def get_header(self, step):
        """
        Generate the header present at the top of LSF execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
                  the parameter step.
        """
        batch_header = dict(self._batch)
        batch_header["nodes"] = step.run.get("nodes", self._batch["nodes"])
        batch_header["job-name"] = step.name.replace(" ", "_")
        batch_header["output"] = "{}.%J.out".format(batch_header["job-name"])
        batch_header["error"] = "{}.%J.err".format(batch_header["job-name"])

        # Updte the batch header with the values from the step's resources
        batch_header.update(
            {
                resource: value for (resource, value) in step.run.items()
                if value
            }
        )

        # LSF requires an hour and minutes format. We need to attempt to split
        # and correct if we get something that's coming in as HH:MM:SS
        walltime = step.run.get("walltime")
        wt_split = walltime.split(":")
        if len(wt_split) == 3:
            # If wall time is specified in three parts, we'll just calculate
            # the minutes off of the seconds and then shift up to hours if
            # needed.
            seconds_minutes = ceil(float(wt_split[2])/60)
            total_minutes = int(wt_split[1]) + seconds_minutes
            hours = int(wt_split[0]) + int(total_minutes/60)
            total_minutes %= 60
            walltime = "{:02d}:{:02d}".format(hours, int(total_minutes))

        batch_header["walltime"] = walltime

        modified_header = ["#!{}".format(self._exec)]
        for key, value in self._header.items():
            if key in batch_header:
                modified_header.append(value.format(**batch_header))

        return "\n".join(modified_header)

    def get_parallelize_command(self, procs, nodes=None, **kwargs):
        """
        Generate the LSF parallelization segement of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
                      (default = 1).
        :returns: A string of the parallelize command configured using nodes
                  and procs.
        """

        args = [self._cmd_flags["cmd"]]

        # Processors segment, checking
        # Need to account for processors per rs -> tasks per rs
        rs_per_node = kwargs.get("rs per node", 1)
        tasks_per_rs = kwargs.get("tasks per rs", 1)

        if int(procs) > int((int(rs_per_node)*int(nodes)*int(tasks_per_rs))):

            LOGGER.error("Resource Specification Error: 'procs' (%s)"
                         " must be a multiple of "
                         "'rs per node' * 'nodes' * 'tasks per rs' (%s)"
                         " where 'rs per node' = %s, 'nodes' = %s, and"
                         " 'tasks per rs' = %s",
                         procs,
                         rs_per_node*nodes*tasks_per_rs,
                         rs_per_node,
                         nodes,
                         tasks_per_rs)
            
        if nodes:
            rs_tasks = int(rs_per_node)*int(nodes)*int(tasks_per_rs)
            if (int(procs) > rs_tasks) or (int(procs) % rs_tasks) > 0:
                LOGGER.error("Resource Specification Error: 'procs' (%s)"
                             " must be a multiple of "
                             "'rs per node' * 'nodes' * 'tasks per rs' (%s)"
                             " where 'rs per node' = %s, 'nodes' = %s, and"
                             " 'tasks per rs' = %s",
                             procs,
                             int(rs_per_node)*int(nodes)*int(tasks_per_rs),
                             rs_per_node,
                             nodes,
                             tasks_per_rs)

        else:
            # NOTE: is this case even allowed on lsf allocations? will it auto
            #       compute the number of nodes on the allocation if scheduling
            #       this to a reservation?  If so, might want to revisit
            rs_tasks = int(rs_per_node)*int(tasks_per_rs)
            if int(procs) > rs_tasks or int(procs) % rs_tasks > 0:
                LOGGER.error("Resource Specification Error: 'procs' (%s)"
                             " must be a multiple of "
                             "'rs per node' * 'tasks per rs' (%s)"
                             " where 'rs per node' = {}, and"
                             " 'tasks per rs' = %s",
                             procs,
                             int(rs_per_node)*int(tasks_per_rs),
                             rs_per_node,
                             tasks_per_rs)

        args += [
            self._cmd_flags["ntasks"],
            str(procs)
        ]

        # Binding
        bind = kwargs.get("bind", "rs")
        args += [
            self._cmd_flags["bind"],
            str(bind)
        ]

        # If we have GPUs being requested, add them to the command.
        gpus = kwargs.get("gpus", 0)
        if not gpus:     # Initialized to "" in study step, FIX THIS
            gpus = 0
        if gpus:
            args += [
                self._cmd_flags["gpus"],
                str(gpus)
            ]

        # Optional gpu binding -> LSF 10.1+
        bind_gpus = kwargs.get("bind gpus", None)
        if bind_gpus:
            args += [
                self._cmd_flags["bind gpus"],
                str(bind_gpus)
            ]

        # handle mappings from node/procs to tasks/rs/nodes

        cpus_per_rs = kwargs.get("cpus per rs", 1)
        if not cpus_per_rs:     # Initialized to "" in study step, FIX THIS
            cpus_per_rs = 1

        args += [self._cmd_flags['tasks per rs'],
                 str(tasks_per_rs)]

        args += [self._cmd_flags['rs per node'],
                 str(rs_per_node)]

        args += [self._cmd_flags['cpus per rs'],
                 str(cpus_per_rs)]

        return " ".join(args)

    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Submit a script to the LSF scheduler.

        :param step: The StudyStep instance this submission is based on.
        :param path: Local path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A dictionary mapping step names to their job
                        identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return status of the submission command and job
                  identiifer.
        """
        args = ["bsub"]
        args += ["-cwd", cwd, "<", path]
        cmd = " ".join(args)
        LOGGER.debug("cwd = %s", cwd)
        LOGGER.debug("Command to execute: %s", cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, cwd=cwd, env=env)
        output, err = p.communicate()
        retcode = p.wait()
        output = output.decode("utf-8")

        # TODO: We need to check for dependencies here. The sbatch is where
        # dependent batch jobs are specified. If we're trying to launch
        # everything at once then that should happen here.

        if retcode == 0:
            LOGGER.info("Submission returned status OK.")
            return SubmissionRecord(
                SubmissionCode.OK, retcode,
                re.search('[0-9]+', output).group(0))
        else:
            LOGGER.warning("Submission returned an error.")
            return SubmissionRecord(SubmissionCode.ERROR, retcode, -1)

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
        # -o = status output formatting
        o_format = "jobid:7 stat:5 exit_code:10 exit_reason:50 delimiter='|'"
        stat_cmd = "bjobs -a -u $USER -o \"{}\""
        cmd = stat_cmd.format(o_format)
        LOGGER.debug("bjobs cmd = \"%s\"", cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        retcode = p.wait()
        output = output.decode("utf-8")

        status = {}
        for jobid in joblist:
            LOGGER.debug("Looking for jobid %s", jobid)
            status[jobid] = None

        state_index = 1
        jobid_index = 0
        term_reason = 3
        if retcode == 0:
            # It seems that LSF may still return 0 even if it found nothing.
            # We'll explicitly check for a "^No " regex in the event that the
            # system is configured to return 0.
            no_jobs = re.search(self.NOJOB_REGEX, output)
            if no_jobs:
                LOGGER.warning("User '%s' has no jobs executing. Returning.",
                               getpass.getuser())
                return JobStatusCode.NOJOBS, {}

            # Otherwise, we can just process as normal.
            for job in output.split("\n")[1:]:
                LOGGER.debug("Job Entry: %s", job)
                # The squeue command output is split with the following indices
                # used for specific information:
                # 0 - Job Identifier
                # 1 - Status of the job
                # 2 - Exit code application terminated with
                # 3 - Reason for termination (if applicable)
                job_split = [x.strip() for x in job.split("|")]
                LOGGER.debug("Entry split: %s", job_split)
                if len(job_split) < 4:
                    LOGGER.debug(
                        "Entry has less than 4 fields. Skipping.",
                        job_split)
                    continue

                while job_split[0] == "":
                    LOGGER.debug("Removing blank entry from head of status.")
                    job_split = job_split[1:]

                if not job_split:
                    LOGGER.debug("Continuing...")
                    continue

                if job_split[jobid_index] in status:
                    if job_split[state_index] == "EXIT":
                        if "TERM_RUNLIMIT" in job_split[term_reason]:
                            _j_state = "TIMEOUT"
                        elif "TERM_OWNER" in job_split[term_reason]:
                            _j_state = "CANCELLED"
                        else:
                            _j_state = job_split[state_index]
                    else:
                        _j_state = job_split[state_index]
                    _state = self._state(_j_state)
                    LOGGER.debug("ID Found. %s -- %s",
                                 job_split[state_index],
                                 _state)
                    status[job_split[jobid_index]] = _state

            return JobStatusCode.OK, status
        # NOTE: We're keeping this here for now since we could see it in the
        # future...
        elif retcode == 255:
            LOGGER.warning("User '%s' has no jobs executing. Returning.",
                           getpass.getuser())
            return JobStatusCode.NOJOBS, status
        else:
            LOGGER.error("Error code '%s' seen. Unexpected behavior "
                         "encountered.", retcode)
            return JobStatusCode.ERROR, status

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
        """
        # If we don't have any jobs to check, just return status OK.
        if not joblist:
            return CancelCode.OK

        cmd = "bkill {}".format(" ".join(joblist))
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        retcode = p.wait()

        if retcode == 0:
            return CancellationRecord(CancelCode.OK, retcode)
        else:
            LOGGER.error("Error code '%s' seen. Unexpected behavior "
                         "encountered.", retcode)
            return CancellationRecord(CancelCode.ERROR, retcode)

    def _state(self, lsf_state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param slurm_state: String representation of scheduler job status.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        # NOTE: fdinatale -- If I'm understanding this correctly, there are
        # four naturally occurring states (excluding states of suspension.)
        # This is somewhat problematic because we don't actually get a time out
        # status here. We probably need to start considering what to do with
        # the post and pre monikers in steps.
        LOGGER.debug("Received LSF State -- %s", lsf_state)
        if lsf_state == "RUN":
            return State.RUNNING
        elif lsf_state == "PEND":
            return State.PENDING
        elif lsf_state == "DONE":
            return State.FINISHED
        elif lsf_state == "CANCELLED":
            return State.CANCELLED
        elif lsf_state == "EXIT":
            return State.FAILED
        elif lsf_state == "TIMEOUT":
            return State.TIMEDOUT
        elif lsf_state == "WAIT" or lsf_state == "PROV":
            return State.WAITING
        elif lsf_state == "UNKWN":
            return State.UNKNOWN
        else:
            return State.UNKNOWN

    def _write_script(self, ws_path, step):
        """
        Write a LSF script to the workspace of a workflow step.

        The job_map optional parameter is a map of workflow step names to job
        identifiers. This parameter so far is only planned to be used when a
        study is configured to be launched in one go (more or less a script
        chain using a scheduler's dependency setting). The functionality of
        the parameter may change depending on both future intended use.

        :param ws_path: Path to the workspace directory of the step.
        :param step: An instance of a StudyStep.
        :returns: Boolean value (True if to be scheduled), the path to the
                  written script for run["cmd"], and the path to the script
                  written for run["restart"] (if it exists).
        """
        to_be_scheduled, cmd, restart = self.get_scheduler_command(step)

        fname = "{}.{}".format(step.name, self._extension)
        script_path = os.path.join(ws_path, fname)
        with open(script_path, "w") as script:
            if to_be_scheduled:
                script.write(self.get_header(step))
            else:
                script.write("#!{}".format(self._exec))

            cmd = "\n\n{}\n".format(cmd)
            script.write(cmd)

        if restart:
            rname = "{}.restart.{}".format(step.name, self._extension)
            restart_path = os.path.join(ws_path, rname)

            with open(restart_path, "w") as script:
                if to_be_scheduled:
                    script.write(self.get_header(step))
                else:
                    script.write("#!{}".format(self._exec))

                cmd = "\n\n{}\n".format(restart)
                script.write(cmd)
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path

    @property
    def extension(self):
        return self._extension
