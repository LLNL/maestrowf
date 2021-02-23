import logging
import os

from maestrowf.abstracts.interfaces import SchedulerScriptAdapter
from maestrowf.abstracts.enums import JobStatusCode, State, SubmissionCode, \
    CancelCode
from maestrowf.interfaces.script import CancellationRecord, SubmissionRecord
from pyaestro.utilities.executor import Executor, ExecTaskState, ExecCancel

LOGGER = logging.getLogger(__name__)


class LocalPoolAdapter(SchedulerScriptAdapter):
    """Interface class for the flux scheduler (on Spectrum MPI)."""

    key = "local_pool"

    def __init__(self, **kwargs):
        """
        Initialize an instance of the LocalPool Adapter.

        The expected keyword arguments that are expected when the Flux adapter
        is instantiated are as follows:
        * num_processes: The number of local workers for processing.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        super(LocalPoolAdapter, self).__init__(**kwargs)
        num_workers = kwargs.get("num_workers", "1")
        self.add_batch_parameter("max_workers", num_workers)
        self._pool = Executor(num_workers)
        self._extension = ".lp.sh"

    @property
    def extension(self):
        return self._extension

    def get_header(self, step):
        """
        Generate the header present at the top of Flux execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
                  the parameter step.
        """
        return f"#!{self._exec}"

    def get_parallelize_command(self, procs, nodes=None, **kwargs):
        """
        Generate an empty parallelize command for local execution.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
                      (default = 1).
        :returns: A string of the parallelize command configured using nodes
                  and procs.
        """
        return ""

    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Submit a script to the Flux scheduler.

        :param step: The StudyStep instance this submission is based on.
        :param path: Local path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A dictionary mapping step names to their job
                        identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return status of the submission command and job
                  identifier.
        """
        try:
            job_id = self._pool.submit(path, cwd)
            ret_code = 0
            submit_status = SubmissionCode.OK
        except Exception as exception:
            LOGGER.error("Encountered exception: %s", str(exception))
            job_id = -1
            ret_code = -1
            submit_status = SubmissionCode.ERROR

        return SubmissionRecord(submit_status, ret_code, job_id)

    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        This method uses the scontrol show job <jobid> command and does a
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
        if not isinstance(joblist, list):
            LOGGER.debug("Specified parameter is not a list.")
            if isinstance(joblist, int):
                LOGGER.debug("Integer found.")
                joblist = [joblist]
            else:
                LOGGER.debug("Unknown type. Returning an error.")
                return JobStatusCode.ERROR, {}

        status = {jid: State.UNKNOWN for jid in joblist}
        try:
            for job_id, state in self._pool.get_all_status():
                if job_id in status:
                    status[job_id] = self._state(state)
            chk_status = JobStatusCode.OK

        except Exception as exception:
            LOGGER.error(str(exception))
            chk_status = JobStatusCode.ERROR

        return chk_status, status

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
        """
        # If we don"t have any jobs to check, just return status OK.
        if not joblist:
            return CancelCode.OK

        c_status = set()
        for job in joblist:
            c_status.add(self._pool.cancel(job))

        c_return = CancelCode.OK
        ret_code = 0
        if ExecCancel.FAILED in c_status:
            c_return = CancelCode.ERROR
            ret_code = -1
        elif ExecCancel.JOBNOTFOUND in c_status:
            ret_code = 1

        return CancellationRecord(c_return, ret_code)

    def _state(self, executor_state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param executor_state: Enum representation of scheduler job status.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        if executor_state == ExecTaskState.PENDING:
            return State.PENDING
        elif executor_state == ExecTaskState.RUNNING:
            return State.RUNNING
        elif executor_state == ExecTaskState.INITIALIZED:
            return State.INITIALIZED
        elif executor_state == ExecTaskState.CANCELLED:
            return State.CANCELLED
        elif executor_state == ExecTaskState.FAILED:
            return State.FAILED
        elif executor_state == ExecTaskState.SUCCESS:
            return State.FINISHED
        else:
            return State.UNKNOWN

    def _write_script(self, ws_path, step):
        """
        Write a script to the workspace of a workflow step.

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
        to_be_scheduled = True

        file_name = f"{step.name}{self.extension}"
        script_path = os.path.join(ws_path, file_name)
        with open(script_path, "w") as script:
            script.write(f"{self.get_header(step)}\n{cmd}")

        if restart:
            restart_name = f"{step.name}.restart{self.extension}"
            restart_path = os.path.join(ws_path, restart_name)

            with open(restart_path, "w") as script:
                script.write(f"{self.get_header(step)}\n{restart}")
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path
