"""Module for the execution of DAG workflows."""
from collections import deque, OrderedDict
from datetime import datetime
import getpass
import logging
import os
import random
import shutil
import tempfile
from time import sleep
from filelock import FileLock, Timeout

from maestrowf.abstracts import PickleInterface
from maestrowf.abstracts.enums import JobStatusCode, State, SubmissionCode, \
    CancelCode, StudyStatus
from maestrowf.datastructures.dag import DAG
from maestrowf.datastructures.environment import Variable
from maestrowf.interfaces import ScriptAdapterFactory
from maestrowf.utils import create_parentdir, get_duration, \
    round_datetime_seconds

LOGGER = logging.getLogger(__name__)
SOURCE = "_source"


class _StepRecord:
    """
    A simple container object representing a workflow step record.

    The record contains all information used to generate associated scripts,
    and settings for execution of the record. The StepRecord is a utility
    class to the ExecutionGraph and maintains all information for any given
    step in the DAG.
    """

    def __init__(self, workspace, step, **kwargs):
        """
        Initialize a new instance of a StepRecord.

        Used kwargs:
        workspace: The working directory of the record.
        status: The record's current execution state.
        jobid: A scheduler assigned job identifier.
        script: The main script used for executing the record.
        restart_script: Script to resume record execution (if applicable).
        to_be_scheduled: True if the record needs scheduling. False otherwise.
        step: The StudyStep that is represented by the record instance.
        restart_limit: Upper limit on the number of restart attempts.
        tmp_dir: A provided temp directory to write scripts to instead of step
        workspace.
        """
        self.workspace = Variable("WORKSPACE", workspace)
        step.run["cmd"] = self.workspace.substitute(step.run["cmd"])
        step.run["restart"] = self.workspace.substitute(step.run["restart"])

        self.jobid = kwargs.get("jobid", [])
        self.script = kwargs.get("script", "")
        self.restart_script = kwargs.get("restart", "")
        self.to_be_scheduled = False
        self.step = step
        self.restart_limit = kwargs.get("restart_limit", 3)

        # Status Information
        self._num_restarts = 0
        self._submit_time = None
        self._start_time = None
        self._end_time = None
        self.status = kwargs.get("status", State.INITIALIZED)

        # Parameter info
        self._params = None

    def add_params(self, params):
        """
        Attaches param names/values used in this step

        :param params: Iterable of tuples of param names, values
        """
        self._params = {param: value for param, value in params}

    @property
    def params(self):
        if not self._params:
            self._params = {}
        return self._params

    def setup_workspace(self):
        """Initialize the record's workspace."""
        create_parentdir(self.workspace.value)

    def generate_script(self, adapter, tmp_dir=""):
        """
        Generate the script for executing the workflow step.

        :param adapter: Instance of adapter to be used for script generation.
        :param tmp_dir: If specified, place generated script in the specified
        temp directory.
        """
        if tmp_dir:
            scr_dir = tmp_dir
        else:
            scr_dir = self.workspace.value

        self.step.run["cmd"] = self.workspace.substitute(self.step.run["cmd"])

        LOGGER.info("Generating script for %s into %s", self.name, scr_dir)
        self.to_be_scheduled, self.script, self.restart_script = \
            adapter.write_script(scr_dir, self.step)
        LOGGER.debug("STEP: %s", self.step)
        LOGGER.info("Script: %s\nRestart: %s\nScheduled?: %s",
                    self.script, self.restart_script, self.to_be_scheduled)

    def execute(self, adapter):
        self.mark_submitted()
        retcode, jobid = self._execute(adapter, self.script)

        if retcode == SubmissionCode.OK:
            self.jobid.append(jobid)

        return retcode

    def restart(self, adapter):
        retcode, jobid = self._execute(adapter, self.restart_script)

        if retcode == SubmissionCode.OK:
            self.jobid.append(jobid)

        return retcode

    @property
    def can_restart(self):
        """
        Get whether or not the record can be restarted.

        :returns: True if the record has a restart command assigned to it.
        """
        if self.restart_script:
            return True

        return False

    def _execute(self, adapter, script):
        if self.to_be_scheduled:
            srecord = adapter.submit(
                self.step, script, self.workspace.value)
        else:
            self.mark_running()
            ladapter = ScriptAdapterFactory.get_adapter("local")()
            srecord = ladapter.submit(
                self.step, script, self.workspace.value)

        retcode = srecord.submission_code
        jobid = srecord.job_identifier
        return retcode, jobid

    def mark_submitted(self):
        """Mark the submission time of the record."""
        LOGGER.debug(
            "Marking %s as submitted (PENDING) -- previously %s",
            self.name,
            self.status)
        self.status = State.PENDING
        if not self._submit_time:
            self._submit_time = round_datetime_seconds(datetime.now())
        else:
            LOGGER.warning(
                "Cannot set the submission time of '%s' because it has "
                "already been set.", self.name
            )

    def mark_running(self):
        """Mark the start time of the record."""
        LOGGER.debug(
            "Marking %s as running (RUNNING) -- previously %s",
            self.name,
            self.status)
        self.status = State.RUNNING
        if not self._start_time:
            self._start_time = round_datetime_seconds(datetime.now())

    def mark_end(self, state):
        """
        Mark the end time of the record with associated termination state.

        :param state: State enum corresponding to termination state.
        """
        LOGGER.debug(
            "Marking %s as finished (%s) -- previously %s",
            self.name,
            state,
            self.status)
        self.status = state
        if not self._end_time:
            self._end_time = round_datetime_seconds(datetime.now())

    def mark_restart(self):
        """Mark the end time of the record."""
        LOGGER.debug(
            "Marking %s as restarting (TIMEOUT) -- previously %s",
            self.name,
            self.status)
        self.status = State.TIMEDOUT
        # Designating a restart limit of zero as an unlimited restart setting.
        # Otherwise, if we're less than restart limit, attempt another restart.
        if self.restart_limit == 0 or \
                self._num_restarts < self.restart_limit:
            self._num_restarts += 1
            return True
        else:
            return False

    @property
    def is_local_step(self):
        """Return whether or not this step executes locally."""
        return not self.to_be_scheduled

    @property
    def elapsed_time(self):
        """Compute the elapsed time of the record (includes queue wait)."""
        if self._submit_time and self._end_time:
            # Return the total elapsed time.
            return get_duration(self._end_time - self._submit_time)
        elif self._submit_time and self.status == State.RUNNING:
            # Return the current elapsed time.
            return get_duration(datetime.now() - self._submit_time)
        else:
            return "--:--:--"

    @property
    def run_time(self):
        """
        Compute the run time of a record (includes restart queue time).

        :returns: A string of the records's run time.
        """
        if self._start_time and self._end_time:
            # If start and end time is set -- calculate run time.
            return get_duration(self._end_time - self._start_time)
        elif self._start_time and not self.status == State.RUNNING:
            # If start time but no end time, calculate current duration.
            return get_duration(datetime.now() - self._start_time)
        else:
            # Otherwise, return an uncalculated marker.
            return "--:--:--"

    @property
    def name(self):
        """
        Get the name of the step represented by the record instance.

        :returns: The name of the StudyStep contained within the record.
        """
        return self.step.real_name

    @property
    def walltime(self):
        """
        Get the requested wall time of the record instance.

        :returns: A string representing the requested computing time.
        """
        return self.step.run["walltime"]

    @property
    def time_submitted(self):
        """
        Get the time the step started.

        :returns: A formatted string of the date and time the step started.
        """
        if self._submit_time:
            return str(self._submit_time)
        else:
            return "--"

    @property
    def time_start(self):
        """
        Get the time the step started.

        :returns: A formatted string of the date and time the step started.
        """
        if self._start_time:
            return str(self._start_time)
        else:
            return "--"

    @property
    def time_end(self):
        """
        Get the time the step ended.

        :returns: A formatted string of the date and time the step ended.
        """
        if self._end_time:
            return str(self._end_time)
        else:
            return "--"

    @property
    def restarts(self):
        """
        Get the number of restarts the step has executed.

        :returns: An int representing the number of restarts.
        """
        return self._num_restarts


class ExecutionGraph(DAG, PickleInterface):
    """
    Datastructure that tracks, executes, and reports on study execution.

    The ExecutionGraph is used to manage, monitor, and interact with tasks and
    the scheduler. This class searches its graph for tasks that are ready to
    run, marks tasks as complete, and schedules ready tasks.

    The Execution class is where functionality for checking task status, logic
    for managing and automatically directing and manipulating the workflow
    should go. Essentially, if logic is needed to automatically manipulate the
    workflow in some fashion or additional monitoring is needed, this class is
    where that would go.
    """

    def __init__(self, submission_attempts=1, submission_throttle=0,
                 use_tmp=False, dry_run=False):
        """
        Initialize a new instance of an ExecutionGraph.

        :param submission_attempts: Number of attempted submissions before
            marking a step as failed.
        :param submission_throttle: Maximum number of scheduled in progress
        submissions.
        :param use_tmp: A Boolean value that when set to 'True' designates
        that ExecutionGraph should use temporary files for output.
        """
        super(ExecutionGraph, self).__init__()
        # Member variables for execution.
        self._adapter = None
        self._description = OrderedDict()

        # Generate tempdir (if specfied)
        if use_tmp:
            self._tmp_dir = tempfile.mkdtemp()
        else:
            self._tmp_dir = ""

        # Sets to track progress.
        self.completed_steps = set([SOURCE])
        self.in_progress = set()
        self.failed_steps = set()
        self.cancelled_steps = set()
        self.ready_steps = deque()
        self.is_canceled = False

        self._status_order = 'bfs'  # Set status order type
        self._status_subtree = None  # Cache bfs_subtree for status writing

        # Values for management of the DAG. Things like submission attempts,
        # throttling, etc. should be listed here.
        self._submission_attempts = submission_attempts
        self._submission_throttle = submission_throttle
        self.dry_run = dry_run

        # A map that tracks the dependencies of a step.
        # NOTE: I don't know how performant the Python dict structure is, but
        # we'll use it for now. I think this may want to be changed to an AVL
        # tree or something of that nature to guarantee worst case performance.
        self._dependencies = {}

        LOGGER.info(
            "\n------------------------------------------\n"
            "Submission attempts =       %d\n"
            "Submission throttle limit = %d\n"
            "Use temporary directory =   %s\n"
            "Tmp Dir = %s\n"
            "------------------------------------------",
            submission_attempts, submission_throttle, use_tmp, self._tmp_dir
        )

        # Error check that the submission values are valid.
        if self._submission_attempts < 1:
            _msg = "Submission attempts should always be greater than 0. " \
                   "Received a value of {}.".format(self._submission_attempts)
            LOGGER.error(_msg)
            raise ValueError(_msg)

        if self._submission_throttle < 0:
            _msg = "Throttling should be 0 for unthrottled or a positive " \
                   "integer for the number of allowed inflight jobs. " \
                   "Received a value of {}.".format(self._submission_throttle)
            LOGGER.error(_msg)
            raise ValueError(_msg)

    def _check_tmp_dir(self):
        """Check and recreate the tempdir should it have been erased."""
        # If we've specified a tmp dir and the previous tmp dir doesn't exist
        # recreate it.
        if self._tmp_dir and not os.path.exists(self._tmp_dir):
            self._tmp_dir = tempfile.mkdtemp()

    def add_step(self, name, step, workspace, restart_limit, params=None):
        """
        Add a StepRecord to the ExecutionGraph.

        :param name: Name of the step to be added.
        :param step: StudyStep instance to be recorded.
        :param workspace: Directory path for the step's working directory.
        :param restart_limit: Upper limit on the number of restart attempts.
        :param params: Iterable of tuples of step parameter names, values
        """
        data = {
                    "step":          step,
                    "state":         State.INITIALIZED,
                    "workspace":     workspace,
                    "restart_limit": restart_limit,
                }
        record = _StepRecord(**data)
        if params:
            record.add_params(params)

        self._dependencies[name] = set()
        super(ExecutionGraph, self).add_node(name, record)

    def add_connection(self, parent, step):
        """
        Add a connection between two steps in the ExecutionGraph.

        :param parent: The parent step that is required to execute 'step'
        :param step: The dependent step that relies on parent.
        """
        self.add_edge(parent, step)
        self._dependencies[step].add(parent)

    def set_adapter(self, adapter):
        """
        Set the adapter used to interface for scheduling tasks.

        :param adapter: Adapter name to be used when launching the graph.
        """
        if not adapter:
            # If we have no adapter specified, assume sequential execution.
            self._adapter = None
            return

        if not isinstance(adapter, dict):
            msg = "Adapter settings must be contained in a dictionary."
            LOGGER.error(msg)
            raise TypeError(msg)

        # Check to see that the adapter type is something the
        if adapter["type"] not in ScriptAdapterFactory.get_valid_adapters():
            msg = "'{}' adapter must be specfied in ScriptAdapterFactory." \
                  .format(adapter)
            LOGGER.error(msg)
            raise TypeError(msg)

        self._adapter = adapter

    def add_description(self, name, description, **kwargs):
        """
        Add a study description to the ExecutionGraph instance.

        :param name: Name of the study.
        :param description: Description of the study.
        """
        self._description["name"] = name
        self._description["description"] = description
        self._description.update(kwargs)

    @property
    def name(self):
        """
        Return the name for the study in the ExecutionGraph instance.

        :returns: A string of the name of the study.
        """
        return self._description["name"]

    @name.setter
    def name(self, value):
        """
        Set the name for the study in the ExecutionGraph instance.

        :param name: A string of the name for the study.
        """
        self._description["name"] = value

    @property
    def description(self):
        """
        Return the description for the study in the ExecutionGraph instance.

        :returns: A string of the description for the study.
        """
        return self._description["description"]

    @description.setter
    def description(self, value):
        """
        Set the description for the study in the ExecutionGraph instance.

        :param value: A string of the description for the study.
        """
        self._description["description"] = value

    def log_description(self):
        """Log the description of the ExecutionGraph."""
        desc = ["{}: {}".format(key, value)
                for key, value in self._description.items()]
        desc = "\n".join(desc)
        LOGGER.info(
            "\n==================================================\n"
            "%s\n"
            "==================================================\n",
            desc
        )

    def generate_scripts(self):
        """
        Generate the scripts for all steps in the ExecutionGraph.

        The generate_scripts method scans the ExecutionGraph instance and uses
        the stored adapter to write executable scripts for either local or
        scheduled execution. If a restart command is specified, a restart
        script will be generated for that record.
        """
        # An adapter must be specified
        if not self._adapter:
            msg = "Adapter not found. Specify a ScriptAdapter using " \
                  "set_adapter."
            LOGGER.error(msg)
            raise ValueError(msg)

        # Set up the adapter.
        LOGGER.info("Generating scripts...")
        adapter = ScriptAdapterFactory.get_adapter(self._adapter["type"])
        adapter = adapter(**self._adapter)

        self._check_tmp_dir()
        for key, record in self.values.items():
            if key == SOURCE:
                continue

            # Record generates its own script.
            record.setup_workspace()
            record.generate_script(adapter, self._tmp_dir)

    def _execute_record(self, record, adapter, restart=False):
        """
        Execute a StepRecord.

        :param record: The StepRecord to be executed.
        :param adapter: An instance of the adapter to be used for cluster
        submission.
        :param restart: True if the record needs restarting, False otherwise.
        """
        # Logging for debugging.
        LOGGER.info("Calling execute for StepRecord '%s'", record.name)

        num_restarts = 0    # Times this step has temporally restarted.
        retcode = None      # Execution return code.

        # While our submission needs to be submitted, keep trying:
        # 1. If the JobStatus is not OK.
        # 2. num_restarts is less than self._submission_attempts
        self._check_tmp_dir()

        # Only set up the workspace the initial iteration.
        if not restart:
            LOGGER.debug("Setting up workspace for '%s' at %s",
                         record.name, str(datetime.now()))
            # Generate the script for execution on the fly.
            record.setup_workspace()    # Generate the workspace.
            record.generate_script(adapter, self._tmp_dir)

        if self.dry_run:
            record.mark_end(State.DRYRUN)
            self.completed_steps.add(record.name)
            return

        while retcode != SubmissionCode.OK and \
                num_restarts < self._submission_attempts:
            LOGGER.info("Attempting submission of '%s' (attempt %d of %d)...",
                        record.name, num_restarts + 1,
                        self._submission_attempts)

            # We're not restarting -- submit as usual.
            if not restart:
                LOGGER.debug("Calling 'execute' on '%s' at %s",
                             record.name, str(datetime.now()))
                retcode = record.execute(adapter)
            # Otherwise, it's a restart.
            else:
                # If the restart is specified, use the record restart script.
                LOGGER.debug("Calling 'restart' on '%s' at %s",
                             record.name, str(datetime.now()))
                # Generate the script for execution on the fly.
                record.generate_script(adapter, self._tmp_dir)
                retcode = record.restart(adapter)

            # Increment the number of restarts we've attempted.
            LOGGER.debug("Completed submission attempt %d", num_restarts)
            num_restarts += 1
            sleep((random.random() + 1) * num_restarts)

        if retcode == SubmissionCode.OK:
            self.in_progress.add(record.name)

            if record.is_local_step:
                LOGGER.info("Local step %s executed with status OK. Complete.",
                            record.name)
                record.mark_end(State.FINISHED)
                self.completed_steps.add(record.name)
                self.in_progress.remove(record.name)
        else:
            # Find the subtree, because anything dependent on this step now
            # failed.
            LOGGER.warning("'%s' failed to submit properly. "
                           "Step failed.", record.name)
            path, parent = self.bfs_subtree(record.name)
            for node in path:
                self.failed_steps.add(node)
                self.values[node].mark_end(State.FAILED)

        # After execution state debug logging.
        LOGGER.debug("After execution of '%s' -- New state is %s.",
                     record.name, record.status)

    @property
    def status_subtree(self):
        """Cache the status ordering to improve scaling"""
        if not self._status_subtree:
            if self._status_order == 'bfs':
                subtree, _ = self.bfs_subtree("_source")

            elif self._status_order == 'dfs':
                subtree, _ = self.dfs_subtree("_source", par="_source")

            self._status_subtree = [key for key in subtree
                                    if key != '_source']

        return self._status_subtree

    def write_status(self, path):
        """Write the status of the DAG to a CSV file."""
        header = "Step Name,Job ID,Workspace,State,Run Time,Elapsed Time," \
                 "Start Time,Submit Time,End Time,Number Restarts,Params"
        status = [header]

        for key in self.status_subtree:
            value = self.values[key]

            jobid_str = "--"
            if value.jobid:
                jobid_str = str(value.jobid[-1])

            # Include step root in workspace when parameterized
            if list(value.params.items()):
                ws = os.path.join(
                    * os.path.normpath(
                        value.workspace.value).split(os.sep)[-2:]
                )
            else:
                ws = os.path.split(value.workspace.value)[1]

            _ = [
                    value.name, jobid_str,
                    ws,
                    str(value.status.name), value.run_time, value.elapsed_time,
                    value.time_start, value.time_submitted, value.time_end,
                    str(value.restarts),
                    ";".join(["{}:{}".format(param, value)
                              for param, value in value.params.items()])
                ]
            _ = ",".join(_)
            status.append(_)

        stat_path = os.path.join(path, "status.csv")
        lock_path = os.path.join(path, ".status.lock")
        lock = FileLock(lock_path)
        try:
            with lock.acquire(timeout=10):
                with open(stat_path, "w+") as stat_file:
                    stat_file.write("\n".join(status))
        except Timeout:
            pass

    def _check_study_completion(self):
        # We cancelled, return True marking study as complete.
        if self.is_canceled and not self.in_progress:
            LOGGER.info("Cancelled -- completing study.")
            return StudyStatus.CANCELLED

        # check for completion of all steps
        resolved_set = \
            self.completed_steps | self.failed_steps | self.cancelled_steps
        if not set(self.values.keys()) - resolved_set:
            # some steps were cancelled and is_canceled wasn't set
            if len(self.cancelled_steps) > 0:
                logging.info("'%s' was cancelled. Returning.", self.name)
                return StudyStatus.CANCELLED

            # some steps were failures indicating failure
            if len(self.failed_steps) > 0:
                logging.info("'%s' is complete with failures. Returning.",
                             self.name)
                return StudyStatus.FAILURE

            # everything completed were are done
            logging.info("'%s' is complete. Returning.", self.name)
            return StudyStatus.FINISHED

        return StudyStatus.RUNNING

    def execute_ready_steps(self):
        """
        Execute any steps whose dependencies are satisfied.

        The 'execute_ready_steps' method is the core of how the ExecutionGraph
        manages execution. This method does the following:

        * Checks the status of existing jobs that are executing and updates
          the state if changed.
        * Finds steps that are initialized and determines what can be run
          based on satisfied dependencies and executes steps whose
          dependencies are met.

        :returns: True if the study has completed, False otherwise.
        """
        # TODO: We may want to move this to a singleton somewhere
        # so we can guarantee that all steps use the same adapter.
        adapter = ScriptAdapterFactory.get_adapter(self._adapter["type"])
        adapter = adapter(**self._adapter)

        if not self.dry_run:
            LOGGER.debug("Checking status check...")
            retcode, job_status = self.check_study_status()
        else:
            LOGGER.debug("DRYRUN: Skipping status check...")
            retcode = JobStatusCode.OK
            job_status = {}

        LOGGER.debug("Checked status (retcode %s)-- %s", retcode, job_status)

        # For now, if we can't check the status something is wrong.
        # Don't modify the DAG.
        if retcode == JobStatusCode.ERROR:
            msg = "Job status check failed -- Aborting."
            LOGGER.error(msg)
            raise RuntimeError(msg)
        elif retcode == JobStatusCode.OK:
            # For the status of each currently in progress job, check its
            # state.
            cleanup_steps = set()  # Steps that are in progress showing failed.
            cancel_steps = set()   # Steps that have dependencies to mark cancelled
            for name, status in job_status.items():
                LOGGER.debug("Checking job '%s' with status %s.", name, status)
                record = self.values[name]

                if status == State.FINISHED:
                    # Mark the step complete and notate its end time.
                    record.mark_end(State.FINISHED)
                    LOGGER.info("Step '%s' marked as finished. Adding to "
                                "complete set.", name)
                    self.completed_steps.add(name)
                    self.in_progress.remove(name)

                elif status == State.RUNNING:
                    # When detect that a step is running, mark it.
                    LOGGER.info("Step '%s' found to be running.", record.name)
                    record.mark_running()

                elif status == State.TIMEDOUT:
                    # Execute the restart script.
                    # If a restart script doesn't exist, re-run the command.
                    # If we're under the restart limit, attempt a restart.
                    if record.can_restart:
                        if record.mark_restart():
                            LOGGER.info(
                                "Step '%s' timed out. Restarting (%s of %s).",
                                name, record.restarts, record.restart_limit
                            )
                            self._execute_record(record, adapter, restart=True)
                        else:
                            LOGGER.info("'%s' has been restarted %s of %s "
                                        "times. Marking step and all "
                                        "descendents as failed.",
                                        name,
                                        record.restarts,
                                        record.restart_limit)
                            self.in_progress.remove(name)
                            cleanup_steps.update(self.bfs_subtree(name)[0])
                    # Otherwise, we can't restart so mark the step timed out.
                    else:
                        LOGGER.info("'%s' timed out, but cannot be restarted."
                                    " Marked as TIMEDOUT.", name)
                        # Mark that the step ended due to TIMEOUT.
                        record.mark_end(State.TIMEDOUT)
                        # Remove from in progress since it no longer is.
                        self.in_progress.remove(name)
                        # Add the subtree to the clean up steps
                        cleanup_steps.update(self.bfs_subtree(name)[0])
                        # Remove the current step, clean up is used to mark
                        # steps definitively as failed.
                        cleanup_steps.remove(name)
                        # Add the current step to failed.
                        self.failed_steps.add(name)

                elif status == State.HWFAILURE:
                    # TODO: Need to make sure that we do this a finite number
                    # of times.
                    # Resubmit the cmd.
                    LOGGER.warning("Hardware failure detected. Attempting to "
                                   "resubmit step '%s'.", name)
                    # We can just let the logic below handle submission with
                    # everything else.
                    self.ready_steps.append(name)

                elif status == State.FAILED:
                    LOGGER.warning(
                        "Job failure reported. Aborting %s -- flagging all "
                        "dependent jobs as failed.",
                        name
                    )
                    self.in_progress.remove(name)
                    record.mark_end(State.FAILED)
                    cleanup_steps.update(self.bfs_subtree(name)[0])

                elif status == State.UNKNOWN:
                    record.mark_end(State.UNKNOWN)
                    LOGGER.info(
                        "Step '%s' found in UNKNOWN state. Step was found "
                        "in '%s' state previously, marking as UNKNOWN. "
                        "Adding to failed steps.",
                        name, record.status)
                    cleanup_steps.update(self.bfs_subtree(name)[0])
                    self.in_progress.remove(name)

                elif status == State.CANCELLED:
                    LOGGER.info("Step '%s' was cancelled.", name)
                    self.in_progress.remove(name)
                    record.mark_end(State.CANCELLED)
                    cancel_steps.update(self.bfs_subtree(name)[0])

            # Let's handle all the failed steps in one go.
            for node in cleanup_steps:
                self.failed_steps.add(node)
                self.values[node].mark_end(State.FAILED)

            # Handle dependent steps that need cancelling
            for node in cancel_steps:
                self.cancelled_steps.add(node)
                self.values[node].mark_end(State.CANCELLED)

        # Now that we've checked the statuses of existing jobs we need to make
        # sure dependencies haven't been met.
        for key in self.values.keys():
            # We MUST dereference from the key. If we use values.items(), a
            # generator gets produced which will give us a COPY of a record and
            # not the actual record.
            record = self.values[key]

            # A completed step by definition has had its dependencies met.
            # Skip it.
            if key in self.completed_steps:
                LOGGER.debug("'%s' in completed set, skipping.", key)
                continue

            LOGGER.debug("Checking %s -- %s", key, record.jobid)
            # If the record is only INITIALIZED, we have encountered a step
            # that needs consideration.
            if record.status == State.INITIALIZED:
                LOGGER.debug("'%s' found to be initialized. Checking "
                             "dependencies. ", key)

                LOGGER.debug(
                    "Unfulfilled dependencies: %s",
                    self._dependencies[key])

                s_completed = list(filter(
                    lambda x: x in self.completed_steps,
                    self._dependencies[key]))
                self._dependencies[key] = \
                    self._dependencies[key] - set(s_completed)
                LOGGER.debug(
                    "Completed dependencies: %s\n"
                    "Remaining dependencies: %s",
                    s_completed, self._dependencies[key])

                # If the gating dependencies set is empty, we can execute.
                if not self._dependencies[key]:
                    if key not in self.ready_steps:
                        LOGGER.debug("All dependencies completed. Staging.")
                        self.ready_steps.append(key)
                    else:
                        LOGGER.debug("Already staged. Passing.")
                        continue

        # We now have a collection of ready steps. Execute.
        # If we don't have a submission limit, go ahead and submit all.
        if self._submission_throttle == 0:
            LOGGER.info("Launching all ready steps...")
            _available = len(self.ready_steps)
        # Else, we have a limit -- adhere to it.
        else:
            # Compute the number of available slots we have for execution.
            _available = self._submission_throttle - len(self.in_progress)
            # Available slots should never be negative, but on the off chance
            # we are in a slot deficit, then we will just say none are free.
            _available = max(0, _available)
            # Now, we need to take the min of the length of the queue and the
            # computed number of slots. We could have free slots, but have less
            # in the queue.
            _available = min(_available, len(self.ready_steps))
            LOGGER.info("Found %d available slots...", _available)

        for i in range(0, _available):
            # Pop the record and execute using the helper method.
            _record = self.values[self.ready_steps.popleft()]

            # If we get to this point and we've cancelled, cancel the record.
            if self.is_canceled:
                LOGGER.info("Cancelling '%s' -- continuing.", _record.name)
                _record.mark_end(State.CANCELLED)
                self.cancelled_steps.add(_record.name)
                continue

            LOGGER.debug("Launching job %d -- %s", i, _record.name)
            self._execute_record(_record, adapter)

        # check the status of the study upon finishing this round of execution
        completion_status = self._check_study_completion()
        return completion_status

    def check_study_status(self):
        """
        Check the status of currently executing steps in the graph.

        This method is used to check the status of all currently in progress
        steps in the ExecutionGraph. Each ExecutionGraph stores the adapter
        used to generate and execute its scripts.
        """
        # Set up the job list and the map to get back to step names.
        joblist = []
        jobmap = {}
        for step in self.in_progress:
            jobid = self.values[step].jobid[-1]
            joblist.append(jobid)
            jobmap[jobid] = step

        # Grab the adapter from the ScriptAdapterFactory.
        adapter = ScriptAdapterFactory.get_adapter(self._adapter["type"])
        adapter = adapter(**self._adapter)
        # Use the adapter to grab the job statuses.
        retcode, job_status = adapter.check_jobs(joblist)
        # Map the job identifiers back to step names.
        step_status = {jobmap[jobid]: status
                       for jobid, status in job_status.items()}

        # Based on return code, log something different.
        if retcode == JobStatusCode.OK:
            LOGGER.info("Jobs found for user '%s'.", getpass.getuser())
            return retcode, step_status
        elif retcode == JobStatusCode.NOJOBS:
            LOGGER.info("No jobs found.")
            return retcode, step_status
        else:
            msg = "Unknown Error (Code = {})".format(retcode)
            LOGGER.error(msg)
            return retcode, step_status

    def cancel_study(self):
        """Cancel the study."""
        joblist = []
        for step in self.in_progress:
            jobid = self.values[step].jobid[-1]
            joblist.append(jobid)

        # Grab the adapter from the ScriptAdapterFactory.
        adapter = ScriptAdapterFactory.get_adapter(self._adapter["type"])
        adapter = adapter(**self._adapter)

        # cancel our jobs
        crecord = adapter.cancel_jobs(joblist)
        self.is_canceled = True

        if crecord.cancel_status == CancelCode.OK:
            LOGGER.info("Successfully requested to cancel all jobs.")
        elif crecord.cancel_status == CancelCode.ERROR:
            LOGGER.error(
                "Failed to cancel jobs. (Code = %s)", crecord.return_code)
        else:
            LOGGER.error("Unknown Error (Code = %s)", crecord.return_code)

        return crecord.cancel_status

    def cleanup(self):
        """Clean up output produced by the ExecutionGraph."""
        if self._tmp_dir:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
