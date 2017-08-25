import getpass
import logging
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
        Initializes a new instance of a StepRecord.

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
        self.status = kwargs.pop("status", State.INITIALIZED)
        self.jobid = kwargs.pop("jobid", [])
        self.script = kwargs.pop("script", "")
        self.restart_script = kwargs.pop("restart", "")
        self.to_be_scheduled = False
        self.step = kwargs.pop("step", None)
        self.restart_limit = kwargs.pop("restart_limit", 3)
        self.num_restarts = 0


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
        Initializes a new instance of an ExecutionGraph.

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
        Generates the scripts for all steps in the ExecutionGraph.

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
                retcode, jobid = adapter.submit(
                    record.step,
                    record.script,
                    record.workspace)
            # Otherwise, it's a restart.
            else:
                # If the restart is specified, use the record restart script.
                retcode, jobid = adapter.submit(
                    record.step,
                    record.restart_script,
                    record.workspace)

            # Increment the number of restarts we've attempted.
            num_restarts += 1

        if retcode == SubmissionCode.OK:
            logger.info("'%s' submitted with identifier '%s'", name, jobid)
            record.status = State.PENDING
            record.jobid.append(jobid)
            self.in_progress.add(name)

            # Executed locally, so if we executed OK -- Finished.
            if record.to_be_scheduled is False:
                self.completed_steps.add(name)
                self.in_progress.remove(name)
                record.state = State.FINISHED
        else:
            # Find the subtree, because anything dependent on this step now
            # failed.
            logger.warning("'%s' failed to properly submit properly. "
                           "Step failed.", name)
            path, parent = self.bfs_subtree(name)
            for node in path:
                self.failed_steps.add(node)
                self.values[node].status = State.FAILED

    def execute_ready_steps(self):
        """
        Executes any steps whose dependencies are satisfied.

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
            cleanup_steps = set()  # Steps that are in progress showing failed.
            for name, status in job_status.items():
                logger.debug("Checking job '%s' with status %s.",
                             name, status)
                record = self.values[name]
                if status == State.FINISHED:
                    # Mark the step complete.
                    logger.info("Step '%s' marked as finished. Adding to "
                                "complete set.", name)
                    self.completed_steps.add(name)
                    record.state = State.FINISHED
                    self.in_progress.remove(name)

                elif status == State.TIMEDOUT:
                    # Execute the restart script.
                    # If a restart script doesn't exist, re-run the command.
                    # If we're under the restart limit, attempt a restart.
                    if record.num_restarts < record.restart_limit:
                        logger.info("Step '%s' timedout. Restarting.", name)
                        self._submit_record(name, record, restart=True)
                        record.num_restarts += 1
                    else:
                        logger.info("'%s' has been restarted %s of %s times. "
                                    "Marking step and all descendents as "
                                    "failed.", name,
                                    record.num_restarts,
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
                    cleanup_steps.update(self.bfs_subtree(name)[0])

            # Let's handle all the failed steps in one go.
            for node in cleanup_steps:
                self.failed_steps.add(node)
                self.values[node].status = State.FAILED

        # Now that we've checked the statuses of existing jobs we need to make
        # sure dependencies haven't been met.
        for key, record in self.values.items():
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
            logger.debug("Record: %s", record.__dict__)
            self._execute_record(key, record)

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
