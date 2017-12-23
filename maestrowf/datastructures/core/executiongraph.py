from datetime import datetime
from filelock import FileLock, Timeout
import getpass
import logging
import os
import pickle

from maestrowf.abstracts.enums import JobStatusCode, State, SubmissionCode
from maestrowf.datastructures.dag import DAG
from maestrowf.interfaces import ScriptAdapterFactory

logger = logging.getLogger(__name__)
SOURCE = "_source"


class _StepRecord(object):
    """
    A simple container object representing a workflow step record.

    The record contains all information used to generate associated scripts,
    and settings for execution of the record. The StepRecord is a utility
    class to the ExecutionGraph and maintains all information for any given
    step in the DAG.
    """

    def __init__(self, **kwargs):
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
        """
        self.workspace = kwargs.pop("workspace", "")

        self.jobid = kwargs.pop("jobid", [])
        self.script = kwargs.pop("script", "")
        self.restart_script = kwargs.pop("restart", "")
        self.to_be_scheduled = False
        self.step = kwargs.pop("step", None)
        self.restart_limit = kwargs.pop("restart_limit", 3)

        # Status Information
        self._num_restarts = 0
        self._submit_time = None
        self._start_time = None
        self._end_time = None
        self.status = kwargs.pop("status", State.INITIALIZED)

    def mark_submitted(self):
        """Mark the submission time of the record."""
        logger.debug(
            "Marking %s as submitted (PENDING) -- previously %s",
            self.name,
            self.status)
        self.status = State.PENDING
        if not self._submit_time:
            self._submit_time = datetime.now()
        else:
            logger.warning(
                "Cannot set the submission time of '%s' because it has"
                "already been set.", self.name
            )

    def mark_running(self):
        """Mark the start time of the record."""
        logger.debug(
            "Marking %s as running (RUNNING) -- previously %s",
            self.name,
            self.status)
        self.status = State.RUNNING
        if not self._start_time:
            self._start_time = datetime.now()

    def mark_end(self, state):
        """
        Mark the end time of the record with associated termination state.

        :param state: State enum corresponding to termination state.
        """
        logger.debug(
            "Marking %s as finised (%s) -- previously %s",
            self.name,
            state,
            self.status)
        self.status = state
        if not self._end_time:
            self._end_time = datetime.now()

    def mark_restart(self):
        """Mark the end time of the record."""
        logger.debug(
            "Marking %s as restarting (TIMEOUT) -- previously %s",
            self.name,
            self.status)
        self.status = State.TIMEDOUT
        if self._num_restarts == self.restart_limit:
            return False
        else:
            self._num_restarts += 1
            return True

    @property
    def elapsed_time(self):
        """Compute the elapsed time of the record (includes queue wait)."""
        if self._submit_time and self._end_time:
            # Return the total elapsed time.
            return str(self._end_time - self._submit_time)
        elif self._submit_time and self.status == State.RUNNING:
            # Return the current elapsed time.
            return str(datetime.now() - self._submit_time)
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
            return str(self._end_time - self._start_time)
        elif self._start_time and not self.status == State.RUNNING:
            # If start time but no end time, calculate current duration.
            return str(datetime.now() - self._start_time)
        else:
            # Otherwise, return an uncalculated marker.
            return "--:--:--"

    @property
    def name(self):
        """
        Get the name of the step represented by the record instance.

        :returns: The name of the StudyStep contained within the record.
        """
        return self.step.name

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


class ExecutionGraph(DAG):
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

    def __init__(self, submission_attempts=1):
        """
        Initialize a new instance of an ExecutionGraph.

        :param submission_attempts: Number of attempted submissions before
        marking a step as failed.
        """
        super(ExecutionGraph, self).__init__()
        # Member variables for execution.
        self._adapter = None
        self._description = {}

        # Sets to track progress.
        self.completed_steps = set([SOURCE])
        self.in_progress = set()
        self.failed_steps = set()

        # Values for management of the DAG. Things like submission attempts,
        # throttling, etc. should be listed here.
        self._submission_attempts = submission_attempts

    def add_step(self, name, step, workspace, restart_limit):
        """
        Add a StepRecord to the ExecutionGraph.

        :param name: Name of the step to be added.
        :param step: StudyStep instance to be recorded.
        :param workspace: Directory path for the step's working directory.
        :param restart_limit: Upper limit on the number of restart attempts.
        """
        data = {
                    "step": step,
                    "state": State.INITIALIZED,
                    "workspace": workspace,
                    "restart_limit": restart_limit
                }
        record = _StepRecord(**data)
        super(ExecutionGraph, self).add_node(name, record)

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
            logger.error(msg)
            raise TypeError(msg)

        # Check to see that the adapter type is something the
        if adapter["type"] not in ScriptAdapterFactory.get_valid_adapters():
            msg = "'{}' adapter must be specfied in ScriptAdapterFactory." \
                  .format(adapter)
            logger.error(msg)
            raise TypeError(msg)

        self._adapter = adapter

    def add_description(self, name, description):
        """
        Add a study description to the ExecutionGraph instance.

        :param name: Name of the study.
        :param description: Description of the study.
        """
        self._description["name"] = name
        self._description["description"] = description

    @classmethod
    def unpickle(cls, path):
        """
        Load an ExecutionGraph instance from a pickle file.

        :param path: Path to a ExecutionGraph pickle file.
        """
        with open(path, 'rb') as pkl:
            dag = pickle.load(pkl)

        if not isinstance(dag, cls):
            msg = "Object loaded from {path} is of type {type}. Expected an" \
                  " object of type '{cls}.'".format(path=path, type=type(dag),
                                                    cls=type(cls))
            logger.error(msg)
            raise TypeError(msg)

        return dag

    def pickle(self, path):
        """
        Generate a pickle file of the graph instance.

        :param path: The path to write the pickle to.
        """
        if not self._adapter:
            msg = "A script adapter must be set before an ExecutionGraph is " \
                  "pickled. Use the 'set_adapter' method to set a specific" \
                  " script interface."
            logger.error(msg)
            raise Exception(msg)

        with open(path, 'wb') as pkl:
            pickle.dump(self, pkl)

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
            logger.error(msg)
            raise ValueError(msg)

        for key, record in self.values.items():
            if key == SOURCE:
                continue

            logger.info("Generating scripts...")
            adapter = ScriptAdapterFactory.get_adapter(self._adapter["type"])
            adapter = adapter(**self._adapter)
            to_be_scheduled, cmd_script, restart_script = \
                adapter.write_script(record.workspace, record.step)
            logger.info("Step -- %s\nScript: %s\nRestart: %s\nScheduled?: %s",
                        record.step.name, cmd_script, restart_script,
                        to_be_scheduled)
            record.to_be_scheduled = to_be_scheduled
            record.script = cmd_script
            record.restart_script = restart_script

    def _execute_record(self, name, record, restart=False):
        """
        Execute a StepRecord.

        :param name: The name of the step to be executed.
        :param record: An instance of a _StepRecord class.
        :param restart: True if the record needs restarting, False otherwise.
        """
        num_restarts = 0    # Times this step has temporally restarted.
        retcode = None      # Execution return code.

        # If we want to schedule the execution of the record, grab the
        # scheduler adapter from the ScriptAdapterFactory.
        if record.to_be_scheduled:
            adapter = \
                ScriptAdapterFactory.get_adapter(self._adapter["type"])
        else:
            # Otherwise, just use the local adapter.
            adapter = \
                ScriptAdapterFactory.get_adapter("local")

        # Pass the adapter the settings we've stored.
        adapter = adapter(**self._adapter)
        # While our submission needs to be submitted, keep trying:
        # 1. If the JobStatus is not OK.
        # 2. num_restarts is less than self._submission_attempts
        while retcode != SubmissionCode.OK and \
                num_restarts < self._submission_attempts:
            logger.info("Attempting submission of '%s' (attempt %d of %d)...",
                        name, num_restarts + 1, self._submission_attempts)

            # If not a restart, submit the cmd script.
            if not restart:
                logger.debug(
                    "'%s' is not restarting -- Marking as SUBMITTED from %s "
                    "at %s",
                    name,
                    record.status,
                    str(datetime.now())
                )
                # Mark the start time.
                record.mark_submitted()
                # If local, we'll execute right away so mark as running.
                if not record.to_be_scheduled:
                    logger.debug(
                        "'%s' running locally -- Marking as RUNNING from %s "
                        "at %s",
                        name,
                        record.status,
                        str(datetime.now())
                    )
                    record.mark_running()

                retcode, jobid = adapter.submit(
                    record.step,
                    record.script,
                    record.workspace)
            # Otherwise, it's a restart.
            else:
                # If the restart is specified, use the record restart script.
                record.mark_running()
                retcode, jobid = adapter.submit(
                    record.step,
                    record.restart_script,
                    record.workspace)

            # Increment the number of restarts we've attempted.
            num_restarts += 1

        if retcode == SubmissionCode.OK:
            logger.info("'%s' submitted with identifier '%s'", name, jobid)
            record.jobid.append(jobid)
            self.in_progress.add(name)

            # Executed locally, so if we executed OK -- Finished.
            if record.to_be_scheduled is False:
                record.mark_end(State.FINISHED)
                self.completed_steps.add(name)
                self.in_progress.remove(name)
        else:
            # Find the subtree, because anything dependent on this step now
            # failed.
            logger.warning("'%s' failed to properly submit properly. "
                           "Step failed.", name)
            path, parent = self.bfs_subtree(name)
            for node in path:
                self.failed_steps.add(node)
                self.values[node].mark_end(State.FAILED)

    def write_status(self, path):
        header = "Step Name,Workspace,State,Run Time,Elapsed Time,Start Time" \
                 ",Submit Time,End Time,Number Restarts"
        status = [header]
        keys = set(self.values.keys()) - set(["_source"])
        for key in keys:
            value = self.values[key]
            _ = [
                    value.name, os.path.split(value.workspace)[1],
                    str(value.status), value.run_time, value.elapsed_time,
                    value.time_start, value.time_submitted, value.time_end,
                    str(value.restarts)
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

    def execute_ready_steps(self):
        """
        Execute any steps whose dependencies are satisfied.

        The 'execute_ready_steps' method is the core of how the ExecutionGraph
        manages execution. This method does the following:
            - Checks the status of existing jobs that are executing.
                - Updates the state if changed.
            - Finds steps that are initialized and determines what can be run:
                - Scans a steps dependencies and stages if all are me.
                - Executes any steps whose dependencies are met.

        :returns: True if the study has completed, False otherwise.
        """
        resolved_set = self.completed_steps | self.failed_steps
        if not set(self.values.keys()) - resolved_set:
            # Just return for now, but we'll need a way to signal that there
            # are no more things to run.
            logging.info("'%s' is complete. Returning.", self.name)
            return True

        ready_steps = {}
        retcode, job_status = self.check_study_status()
        logger.debug("Checked status (retcode %s)-- %s", retcode, job_status)

        # For now, if we can't check the status something is wrong.
        # Don't modify the DAG.
        if retcode == JobStatusCode.ERROR:
            msg = "Job status check failed -- Aborting."
            logger.error(msg)
            raise RuntimeError(msg)
        elif retcode == JobStatusCode.OK:
            # For the status of each currently in progress job, check its
            # state.
            # TODO: We need to mark a record as running if it is detected
            # to be.
            cleanup_steps = set()  # Steps that are in progress showing failed.
            for name, status in job_status.items():
                logger.debug("Checking job '%s' with status %s.",
                             name, status)
                record = self.values[name]
                if status == State.FINISHED:
                    # Mark the step complete and notate its end time.
                    record.mark_end(State.FINISHED)
                    logger.info("Step '%s' marked as finished. Adding to "
                                "complete set.", name)
                    self.completed_steps.add(name)
                    self.in_progress.remove(name)

                elif status == State.RUNNING:
                    # When detect that a step is running, mark it.
                    logger.info("Step '%s' found to be running.")
                    record.mark_running()

                elif status == State.TIMEDOUT:
                    # Execute the restart script.
                    # If a restart script doesn't exist, re-run the command.
                    # If we're under the restart limit, attempt a restart.
                    if record.mark_restart():
                        logger.info(
                            "Step '%s' timed out. Restarting (%s of %s).",
                            name, record.restarts, record.restart_limit
                        )
                        self._submit_record(name, record, restart=True)
                    else:
                        logger.info("'%s' has been restarted %s of %s times. "
                                    "Marking step and all descendents as "
                                    "failed.",
                                    name,
                                    record.restarts,
                                    record.restart_limit)
                        self.in_progress.remove(name)
                        cleanup_steps.update(self.bfs_subtree(name)[0])

                elif status == State.HWFAILURE:
                    # TODO: Need to make sure that we do this a finite number
                    # of times.
                    # Resubmit the cmd.
                    logger.warning("Hardware failure detected. Attempting to "
                                   "resubmit step '%s'.", name)
                    # We can just let the logic below handle submission with
                    # everything else.
                    ready_steps[name] = self.values[name]

                elif status == State.FAILED:
                    logger.warning(
                        "Job failure reported. Aborting %s -- flagging all "
                        "dependent jobs as failed.",
                        name
                    )
                    self.in_progress.remove(name)
                    record.mark_end(State.FAILED)
                    cleanup_steps.update(self.bfs_subtree(name)[0])

            # Let's handle all the failed steps in one go.
            for node in cleanup_steps:
                self.failed_steps.add(node)
                self.values[node].mark_end(State.FAILED)

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
                logger.debug("'%s' in completed set, skipping.", key)
                continue

            logger.debug("Checking %s -- %s", key, record.jobid)
            # If the record is only INITIALIZED, we have encountered a step
            # that needs consideration.
            if record.status == State.INITIALIZED:
                logger.debug("'%s' found to be initialized. Checking "
                             "dependencies...", key)
                # Count the number of its dependencies have finised.
                num_finished = 0
                for dependency in record.step.run["depends"]:
                    logger.debug("Checking '%s'...", dependency)
                    if dependency in self.completed_steps:
                        logger.debug("Found in completed steps.")
                        num_finished += 1
                # If the total number of dependencies finished is the same
                # as the number of dependencies the step has, it's ready to
                # be executed. Add it to the map.
                if num_finished == len(record.step.run["depends"]):
                    logger.debug("All dependencies completed. Staging.")
                    ready_steps[key] = record

        # We now have a collection of ready steps. Execute.
        for key, record in ready_steps.items():
            logger.info("Executing -- '%s'\nScript path = %s", key,
                        record.script)
            logger.debug(
                "Attempting to execute '%s' -- Current state is %s.",
                record.name, record.status
            )
            self._execute_record(key, record)
            logger.debug(
                "After execution of '%s' -- New state is %s.",
                record.name, record.status
            )

        return False

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
            logger.info("Jobs found for user '%s'.", getpass.getuser())
            return retcode, step_status
        elif retcode == JobStatusCode.NOJOBS:
            logger.info("No jobs found.")
            return retcode, step_status
        else:
            msg = "Unknown Error (Code = {retcode})".format(retcode)
            logger.error(msg)
            return retcode, step_status
