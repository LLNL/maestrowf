###############################################################################
# Created by Kevin Ferguson (July 2026)
# at National Science Foundation National Center for Atmospheric Research (NSF NCAR)
# with help from Claude
# The license for the whole repository applies and is reproduced below.
#
# This file is part of MaestroWF, Version: 1.2.1
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

"""Implementation for a PBS Scheduler on NCAR's Derecho"""
import getpass
import logging
from math import ceil
import os
import re

from maestrowf.abstracts.interfaces import SchedulerScriptAdapter
from maestrowf.abstracts.enums import CancelCode, JobStatusCode, State, \
    SubmissionCode
from maestrowf.interfaces.script import CancellationRecord, SubmissionRecord
from maestrowf.utils import make_safe_path, start_process

LOGGER = logging.getLogger(__name__)


class DerechoPBSScriptAdapter(SchedulerScriptAdapter):
    """
    A ScriptAdapter class for interfacing with the PBS scheduler on NCAR's Derecho.
    This adapter is specific to the PBS implementation on NCAR's Derecho
    computer. In general, most commands are compliant with a general PBS
    implementation. However, there are a few aspects of note:
        * `get_parallelize_command` (and `self._cmd_flags`) builds the launch
          command as
            mpiexec -n <procs> -ppn <procs_per_node> -d <cores_per_task>
          A brief search shows that this format may be specific to Derecho and not
          portable to other installations (e.g., the open-mpi docs do not show `-ppn` or `-d` as
          valid flags). This is the main thing that makes this adapter Derecho-specific
        * Exit codes are interpreted as follows:
          - 0: Success
          - > 0: Failure
          - < 0: Timed out (e.g. failed due to exceeding walltime)
          This may not be Derecho-specific, but I haven't done an exhaustive search to say otherwise,
          so it is probably better to have this as a stipulation.
    """

    key = "pbs_derecho"

    def __init__(self, **kwargs):
        """
        Initialize an instance of the PBSScriptAdapter.

        The PBSScriptAdapter is this package's interface to the PBS
        scheduler. This adapter constructs PBS scripts for a StudyStep 
        based on user set defaults and local settings present in each step.

        The expected keyword arguments that are expected when the PBS adapter
        is instantiated are as follows:
        - host: The cluster to execute scripts on.
        - bank: The account to charge computing time to.
        - queue: Scheduler queue scripts should be submitted to.
        - nodes: The number of compute nodes to be reserved for computing.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        super(DerechoPBSScriptAdapter, self).__init__(**kwargs)

        # NOTE: Host doesn't seem to matter for PBS. qsub assumes that the
        # current host is where submission occurs.
        self.add_batch_parameter("nodes", kwargs.pop("nodes", ""))
        self.add_batch_parameter("host", kwargs.pop("host"))
        self.add_batch_parameter("bank", kwargs.pop("bank"))
        self.add_batch_parameter("queue", kwargs.pop("queue"))
        self.add_batch_parameter("reservation", kwargs.pop("reservation", ""))
        self.add_batch_parameter("qos", kwargs.get("qos"))

        # Check for procs separately, as we don't want it in the header if
        # it's not present.
        procs = kwargs.get("procs", None)

        # Placeholder till future refactor to push up into spec ingestion/step
        # parsing.
        self._exclusive = {"allocation": False, "launcher": False}

        if procs:
            self.add_batch_parameter("procs", procs)

        self._header = {
            "queue": "#PBS -q {queue}",
            "bank": "#PBS -A {bank}",
            "walltime": "#PBS -l walltime={walltime}",
            "job-name":
                "#PBS -N {job-name}\n"
                "#PBS -o {job-name}.out\n"
                "#PBS -e {job-name}.err",
            "reservation": "#PBS -l advres={reservation}",
            "qos": "#PBS -l job_priority={qos}",
        }

        self._exclusive_header = "#PBS -l place=excl"

        self._cmd_flags = {
            "cmd": "mpiexec",
            "ntasks": "-n",
            "nodes": "--ppn",
            "cores per task": "-d",
        }

        self._extension = "pbs.sh"
        self._unsupported = set(["cmd", "ntasks", "nodes", "procs per node"])

    def _resolve_mpiprocs(self, procs_per_node, cores_per_task):
        """
        Compute the number of MPI ranks (mpiprocs) to place per node, given
        the number of cores reserved per node (ncpus) and the number of
        cores each rank's task should own (e.g. for OpenMP threading).

        :param procs_per_node: Number of cores (ncpus) reserved per node.
        :param cores_per_task: Number of cores per MPI rank/task.
        :returns: The number of MPI ranks (mpiprocs) to place per node.
        """
        procs_per_node = int(procs_per_node)

        try:
            cores_per_task = int(cores_per_task)
        except (TypeError, ValueError):
            cores_per_task = 1
        if not cores_per_task:
            cores_per_task = 1

        mpiprocs_per_node = int(
            ceil(float(procs_per_node) / float(cores_per_task)))

        if mpiprocs_per_node * cores_per_task > procs_per_node:
            err_msg = \
                "'cores per task' ({}) does not evenly divide the " \
                "requested cores per node ({}). Adjust 'cores per task' " \
                "or 'procs per node' so that mpiprocs * cores per task " \
                "does not exceed ncpus.".format(
                    cores_per_task, procs_per_node)
            LOGGER.error(err_msg)
            raise RuntimeError(err_msg)

        return mpiprocs_per_node

    def get_header(self, step):
        """
        Generate the header present at the top of PBS execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
            the parameter step.
        """
        resources = {}
        resources.update(self._batch)
        resources.update(
            {
                resource: value for (resource, value) in step.run.items()
                if value
            }
        )
        # If neither Procs nor Nodes exist, throw an error
        procs = resources.get("procs")
        nodes = resources.get("nodes")

        if not procs and not nodes:
            err_msg = \
                'No explicit resources specified in {}. At least one' \
                ' of "procs" or "nodes" must be set to a non-zero' \
                ' value.'.format(step.name)
            LOGGER.error(err_msg)
            raise RuntimeError(err_msg)

        resources["job-name"] = step.name.replace(" ", "_")
        resources["comment"] = step.description.replace("\n", " ")

        modified_header = ["#!{}".format(self._exec)]
        for key, value in self._header.items():
            if key not in resources:
                continue

            if resources[key]:
                modified_header.append(value.format(**resources))

        # PBS requires resources to be requested via a 'select' statement
        # specifying node count along with per-node cpu/mpi process counts.
        select_nodes = int(nodes) if nodes else 1
        procs_per_node = resources.get("procs per node")
        if not procs_per_node:
            if procs:
                procs_per_node = int(ceil(float(procs) / float(select_nodes)))
            else:
                procs_per_node = 1

        mpiprocs_per_node = self._resolve_mpiprocs(
            procs_per_node, resources.get("cores per task"))

        select = "select={}:ncpus={}:mpiprocs={}".format(
            select_nodes, procs_per_node, mpiprocs_per_node)

        gpus = resources.get("gpus")
        if gpus:
            select += ":ngpus={}".format(gpus)

        modified_header.append("#PBS -l {}".format(select))

        exclusive = self.resolve_exclusive(
            self._exclusive, resources.get("exclusive", None))

        if exclusive['allocation']:
            modified_header.append(self._exclusive_header)

        return "\n".join(modified_header)

    def get_parallelize_command(self, procs, nodes=None, **kwargs):
        """
        Generate the PBS parallelization segement of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
            (default = 1).
        :returns: A string of the parallelize command configured using nodes
            and procs.
        """
        args = [
            # PBS environments commonly launch parallel jobs with mpiexec.
            self._cmd_flags["cmd"],
            # Processors segment
            self._cmd_flags["ntasks"],
            str(procs)
        ]

        if nodes:
            procs_per_node = kwargs.get("procs per node")
            if not procs_per_node:
                procs_per_node = int(ceil(float(procs) / float(nodes)))

            mpiprocs_per_node = self._resolve_mpiprocs(
                procs_per_node, kwargs.get("cores per task"))

            args += [
                self._cmd_flags["nodes"],
                str(mpiprocs_per_node),
            ]

        supported = set(kwargs.keys()) - self._unsupported
        for key in supported:
            value = kwargs.get(key)
            if key not in self._cmd_flags:
                LOGGER.warning("'%s' is not supported -- omitted.", key)
                continue
            if value:
                args += [
                    self._cmd_flags[key],
                    "{}".format(str(value))
                ]

        return " ".join(args)

    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Submit a script to the PBS scheduler.

        :param step: The StudyStep instance this submission is based on.
        :param path: Local path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A dictionary mapping step names to their job
            identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return status of the submission command and job
            identiifer.
        """
        # PBS sets $PBS_O_WORKDIR to the directory qsub is invoked from, so
        # running qsub with the step's workspace as its cwd is sufficient to
        # thread it through; the script itself cds into $PBS_O_WORKDIR (see
        # _write_script) since the job does not start there automatically.
        cmd = "qsub {}".format(path)

        LOGGER.debug("cwd = %s", cwd)
        LOGGER.debug("Command to execute: %s", cmd)
        p = start_process(cmd, cwd=cwd, env=env)
        output, err = p.communicate()
        retcode = p.wait()

        # TODO: We need to check for dependencies here. The qsub is where
        # dependent batch jobs are specified. If we're trying to launch
        # everything at once then that should happen here.

        if retcode == 0:
            LOGGER.info("Submission returned status OK.")
            jid = output.strip()
            return SubmissionRecord(SubmissionCode.OK, retcode, jid)
        else:
            LOGGER.warning(
                "Submission returned an error (see next line).\n%s", err)
            return SubmissionRecord(SubmissionCode.ERROR, retcode)

    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        This method uses the qstat -f -x <jobid> command and does a
        regex search for job information.

        :param joblist: A list of job identifiers to be queried.
        :returns: The return code of the status query, and a dictionary of job
            identifiers to their status.
        """
        LOGGER.debug("Joblist type -- %s", type(joblist))
        LOGGER.debug("Joblist contents -- %s", joblist)
        if not joblist:
            LOGGER.debug("Empty job list specified.")
            return JobStatusCode.OK, {}

        status = {jobid: None for jobid in joblist}

        # qstat options:
        # -f = full status output, required to get 'job_state'/'Exit_status'
        # -x = also report status for recently completed/historical jobs
        cmd = "qstat -f -x {}".format(" ".join(joblist))
        LOGGER.debug("Using qstat cmd: %s", cmd)
        p = start_process(cmd)
        output, err = p.communicate()
        retcode = p.wait()

        if retcode == 127:
            LOGGER.warning("Could not find 'qstat' command.  Returning."),
            return JobStatusCode.ERROR, status

        # qstat -f output is split into blocks, each starting with a line of
        # the form 'Job Id: <jobid>' followed by indented 'key = value' pairs.
        job_blocks = re.split(r"^Job Id:\s*", output, flags=re.MULTILINE)[1:]
        for block in job_blocks:
            LOGGER.debug("Job Entry: %s", block)
            jobid = block.splitlines()[0].strip()
            if jobid not in status:
                continue

            state_match = re.search(r"job_state\s*=\s*(\S+)", block)
            if not state_match:
                LOGGER.debug("Could not find 'job_state' for '%s'.", jobid)
                continue

            exit_match = re.search(r"Exit_status\s*=\s*(-?[0-9]+)", block)
            exit_status = exit_match.group(1) if exit_match else None

            LOGGER.debug("ID Found. %s -- %s", state_match.group(1),
                         self._state(state_match.group(1), exit_status))
            status[jobid] = self._state(state_match.group(1), exit_status)

        if any(jstatus is None for jstatus in status.values()):
            missing_jobids = [jobid for jobid, jstatus in status.items()
                              if jstatus is None]
            LOGGER.debug(
                "Could not find status for Job Entries using 'qstat': %s",
                ', '.join(str(jobid) for jobid in missing_jobids))

        if all(jstatus is None for jstatus in status.values()):
            LOGGER.warning("User '%s' has no jobs executing. Returning.",
                           getpass.getuser())
            return JobStatusCode.NOJOBS, status

        return JobStatusCode.OK, status

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
        """
        # If we don't have any jobs to check, just return status OK.
        if not joblist:
            return CancellationRecord(CancelCode.OK, 0)

        cmd = "qdel {}".format(" ".join(joblist))
        p = start_process(cmd)
        output, err = p.communicate()
        retcode = p.wait()

        if retcode == 0:
            _record = CancellationRecord(CancelCode.OK, retcode)
        else:
            LOGGER.error("Error code '%s' seen. Unexpected behavior "
                         "encountered.", retcode)
            _record = CancellationRecord(CancelCode.ERROR, retcode)

        return _record

    def _state(self, pbs_state, exit_status=None):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param pbs_state: String representation of scheduler job status, as
            reported by the 'job_state' attribute of 'qstat -f'.
        :param exit_status: The 'Exit_status' attribute of 'qstat -f', used to
            distinguish successful, failed, and timed out completed jobs.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        LOGGER.debug("Received PBS State -- %s", pbs_state)
        if pbs_state == "R":
            return State.RUNNING
        elif pbs_state == "Q" or pbs_state == "H" or pbs_state == "T":
            return State.PENDING
        elif pbs_state == "W" or pbs_state == "S":
            return State.WAITING
        elif pbs_state == "E":
            return State.FINISHING
        elif pbs_state == "F" or pbs_state == "X":
            if exit_status is None:
                return State.FINISHED

            try:
                exit_status = int(exit_status)
            except ValueError:
                return State.FINISHED

            if exit_status == 0:
                return State.FINISHED
            elif exit_status < 0:
                # Negative exit codes are used by PBS to indicate a job that
                # was terminated for exceeding a requested resource limit
                # (e.g. walltime).
                return State.TIMEDOUT
            else:
                return State.FAILED
        else:
            LOGGER.debug(
                "Found unhandled state code '%s' from PBS", pbs_state)
            return State.UNKNOWN

    def _write_script(self, ws_path, step):
        """
        Write a PBS script to the workspace of a workflow step.

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

        fname = "{}.{}".format(step.name, self._extension)
        script_path = make_safe_path(ws_path, fname)

        if to_be_scheduled:
            # PBS jobs do not start execution in the submission directory;
            # $PBS_O_WORKDIR is only set as a reference to it, so the script
            # must cd there itself (see 'submit').
            header = "{}\n\ncd \"$PBS_O_WORKDIR\"".format(self.get_header(step))
        else:
            header = "#!{}".format(self._exec)

        form_cmd = "{0}\n\n{1}\n"
        with open(script_path, "w") as script:
            script.write(form_cmd.format(header, cmd))

        if restart:
            rname = "{}.restart.{}".format(step.name, self._extension)
            restart_path = os.path.join(ws_path, rname)

            with open(restart_path, "w") as script:
                script.write(form_cmd.format(header, restart))
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path

    @property
    def extension(self):
        return self._extension
