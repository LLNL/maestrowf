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

"""Class related to the construction of study campaigns."""

import copy
from enum import Enum
import getpass
import logging
import os
import pickle
from subprocess import PIPE, Popen
import time

from maestrowf.abstracts import SimObject, ScriptAdapter
from maestrowf.abstracts.interfaces import JobStatusCode, SubmissionCode
from maestrowf.datastructures.dag import DAG
from maestrowf.datastructures.environment import Variable
from maestrowf.utils import apply_function, create_parentdir

logger = logging.getLogger(__name__)
SOURCE = "_source"


class State(Enum):
    """Workflow step state enumeration."""

    INITIALIZED = 0
    PENDING = 1
    WAITING = 2
    RUNNING = 3
    FINISHING = 4
    FINISHED = 5
    QUEUED = 6
    FAILED = 7
    INCOMPLETE = 8
    HWFAILURE = 9
    TIMEDOUT = 10
    UNKNOWN = 11


class StudyStep(SimObject):
    """
    Class that represents the data and API for a single study step.

    This class is primarily a 1:1 mapping of a study step in the YAML spec in
    terms of data. The StudyStep's class API should capture all functions that
    a step can be expected to perform, including:
        - Applying a combination of parameters to itself.
        - Tests for equality and non-equality to check for changes.
        - Other -- WIP
    """

    def __init__(self):
        """Object that represents a single workflow step."""
        self.name = ""
        self.description = ""
        self.run = {
                        "cmd": "",
                        "depends": "",
                        "pre": "",
                        "post": "",
                        "restart": "",
                        "nodes": "",
                        "procs": "",
                        "walltime": ""
                    }

    def apply_parameters(self, combo):
        """
        Apply a parameter combination to the StudyStep.

        :param combo: A Combination instance to be applied to a StudyStep.
        :returns: A new StudyStep instance with combo applied to its members.
        """
        # Create a new StudyStep and populate it with substituted values.
        tmp = StudyStep()
        tmp.__dict__ = apply_function(self.__dict__, combo.apply)
        # Return if the new step is modified and the step itself.
        return self.__ne__(tmp), tmp

    def __eq__(self, other):
        """
        Equality operator for the StudyStep class.

        :param other: Object to compare self to.
        : returns: True if other is equal to self, False otherwise.
        """
        if isinstance(other, self.__class__):
            # This works because the classes are currently intefaces over
            # internals that are all based on Python builtin classes.
            # NOTE: This method will need to be reworked if something more
            # complex is done with the class.
            return self.__dict__ == other.__dict__

        return False

    def __ne__(self, other):
        """
        Non-equality operator for the StudyStep class.

        :param other: Object to compare self to.
        : returns: True if other is not equal to self, False otherwise.
        """
        return not self.__eq__(other)


class Study(DAG):
    """
    Collection of high level objects to perform study construction.

    The Study class is part of the meat and potatoes of this whole package. A
    Study object is where the intersection of the major moving parts are
    collected. These moving parts include:
        - ParameterGenerator for getting combinations of user parameters
        - StudyEnvironment for managing and applying the environment to studies
        - Study flow, which is a DAG of the abstract workflow

    The class is responsible for a number of the major key steps in study setup
    as well. Those responsibilities include (but are not limited to):
        - Setting up the workspace where a simulation campaign will be run.
        - Applying the StudyEnvionment to the abstract flow DAG:
            - Creating the global workspace for a study.
            - Setting up the parameterized workspaces for each combination.
            - Acquiring dependencies as specified in the StudyEnvironment.
        - Intelligently constructing the expanded DAG to be able to:
            - Recognize when a step executes in a parameterized workspace
            - Recognize when a step executes in the global workspace
        - Expanding the abstract flow to the full set of specified parameters.

    Future functionality that makes sense to add here:
        - Metadata collection. If we're setting things up here, collect the
        general information. We might even want to venture to say that a set of
        directives may be useful so that they could be placed into Dependency
        classes as hooks for dumping that data automatically.
        - A way of packaging an instance of the class up into something that is
        easy to store in the ExecutionDAG class so that an API can be designed
        in whatever class ends up managing all of this to have machine learning
        applications pipe messages to spin up new studies using the same
        environment.
            - The current solution to this is VERY basic. Currently the plan is
            to write a parameterized specification (not unlike the method of
            using parameterized .dat files for simulators) and just have the ML
            engine string replace those. It's crude because currently we'd have
            to just construct a new environment, with no way to manage
            injecting the new set into an existing workspace.
    """

    def __init__(self, name, description,
                 studyenv=None, parameters=None, steps=None):
        """
        Study object used to represent the full workflow of a study.

        Derived from the DAG data structure. Contains everything that a study
        requires to be expanded with the appropriate substitutions and with
        parameters inserted. This data structure should be the instance the
        future daemon loads in to track progress on a workflow.

        :param name: String representing the name of the Study.
        :param description: A text description of what the study does.
        :param steps: A list of StudySteps in proper workflow order.
        :param studyenv: A populated StudyEnvironment instance.
        :param parameters: A populated Parameters instance.
        :param outpath: The path where the output of the study is written.
        """
        # The basic study information
        self.name = name
        self.description = description

        # Initialized the DAG so we have those structures to be used.
        super(Study, self).__init__()

        # We want deep copies so that properties don't change out from under
        # the Sudy data structure.
        self.environment = copy.deepcopy(studyenv)
        self.parameters = copy.deepcopy(parameters)

        # Isolate the OUTPUT_PATH variable. Even though it should be contained
        # in the environment, it needs to be tweaked for each combination of
        # parameters to isolate their workspaces.
        if self.environment:
            # Attempt to remove the OUTPUT_PATH from the environment.
            self.output = self.environment.find('OUTPUT_PATH')

            # If it doesn't exist, assume the current directory is our output
            # path.
            if self.output is None:
                out_path = os.path.abspath('./')
                self.output = Variable('OUTPUT_PATH', out_path, '$')
                self.environment.add(self.output)
            else:
                self.output.value = os.path.abspath(self.output.value)

        # Flag the study as not having been set up and add the source node.
        self._issetup = False
        self.add_node(SOURCE, None)

        # Settings for handling restarts and submission attempts.
        self._restart_limit = 0
        self._submission_attempts = 0

        # If the user specified a flow in the form of steps, copy those into
        # into the Study object.
        if steps:
            for step in steps:
                # Deep copy because it prevents modifications after the fact.
                self.add_step(copy.deepcopy(step))

    @property
    def output_path(self):
        """
        Property method for the OUTPUT_PATH specified for the study.

        :returns: The string path stored in the OUTPUT_PATH variable.
        """
        return self.output.value

    def add_step(self, step):
        """
        Helper method for adding steps to a Study instance.

        For this helper to be most effective, it recommended to apply steps in
        the order that they will be encountered. The method attempts to be
        intelligent and make the intended edge based on the 'depends' entry in
        a step. When adding steps out of order it's recommended to just use the
         base class DAG functionality and manually make connections.

         :param step: A StudyStep instance to be added to the Study instance.
        """
        # Add the node to the DAG.
        self.add_node(step.name, step)

        # If the step depends on a prior step, create an edge.
        if "depends" in step.run and step.run["depends"]:
            for dependency in step.run["depends"]:
                logger.info("{0} is dependent on {1}. Creating edge ("
                            "{1}, {0})...".format(step.name, dependency))
                self.add_edge(dependency, step.name)
        else:
            # Otherwise, if no other dependency, just execute the step.
            self.add_edge(SOURCE, step.name)

    def walk_study(self, src=SOURCE):
        """
        Walk the study and create a spanning tree.

        :param src: Source node to start the walk.
        :returns: A generator of (parent, node name, node value) tuples.
        """
        # Get a DFS spanning tree of the study. This method should always
        # return a complete tree because _source is flagged as a dependency
        # if a step is added without one.
        # TODO: This method should be fixed to return both parents and nodes.
        path, parents = self.dfs_subtree(src)
        for node in path:
            yield parents[node], node, self.values[node]

    def setup(self, submission_attempts=1, restart_limit=1):
        """
        Method for executing initial setup of a Study.

        The method is used for going through and actually acquiring each
        dependency, substituting variables, sources and labels. Also sets up
        the folder structure for the study.

        :param submission_attempts: Number of attempted submissions before
        marking a step as failed.
        :param restart_limit: Upper limit on the number of times a step with
        a restart command can be resubmitted before it is considered failed.
        :returns: True if the Study is successfully setup, False otherwise.
        """
        # If the study has been set up, just return.
        if self._issetup:
            logger.info("%s is already set up, returning.")
            return True

        self._submission_attempts = submission_attempts
        self._restart_limit = restart_limit

        # Set up the directory structure.
        # TODO: fdinatal - As I implement the high level program (manager and
        # launcher in bin), I'm starting to have questions about whether or
        # not the study set up is the place to handle the output path... it
        # feels like the determination of the output path should be at the
        # higher level.
        out_name = "{}_{}".format(self.name, time.strftime("%Y%m%d-%H%M%S"))
        self.output.value = os.path.join(self.output.value, out_name)

        # Set up the environment if it hasn't been already.
        if not self.environment.is_set_up:
            logger.info("Environment is setting up.")
            self.environment.acquire_environment()

        try:
            create_parentdir(self.output.value)
        except Exception as e:
            logger.error(e.message)
            return False

        # Apply all environment artifcacts and acquire everything.
        for key, node in self.values.items():
            logger.info("Applying to step '%s' of the study '%s'...",
                        key, node)
            if node:
                node.__dict__ = apply_function(
                                    node.__dict__,
                                    self.environment.apply_environment)

        # Flag the study as set up.
        self._issetup = True
        return True

    def _setup_parameterized(self):
        """
        Set up the ExecutionGraph of a parameterized study.

        :returns: The path to the study's global workspace and an expanded
        ExecutionGraph based on the parameters and parameterized workflow
        steps.
        """
        # Construct ExecutionGraph
        dag = ExecutionGraph()
        dag.add_description(**self.description)
        # Items to store that should be reset.
        global_workspace = self.output.value  # Highest ouput dir

        for combo in self.parameters:
            # For each Combination in the parameters...
            logger.info("==================================================")
            logger.info("Expanding study '%s' for combination '%s'",
                        self.name, str(combo))
            logger.info("==================================================")

            # For each step in the Study
            # Walk the study and construct subtree based on the combination.
            for parent, step, node in self.walk_study():
                # If we find the source node, we can just add it and continue.
                if step == SOURCE:
                    logger.debug("Source node found.")
                    dag.add_node(SOURCE, None)
                    continue

                logger.debug("Processing step '%s'.", step)
                # Apply the parameters to the step
                modified, step_exp = node.apply_parameters(combo)

                # Ok so, if we come back from apply_parameters and the step was
                # in fact modified, we know that this step is a unique step
                # due to the parameters being applied (so rename it).
                # Otherwise, it can remain with its given name.
                # If modified, that also affects the workspace path for the
                # step.
                if modified:
                    # Rename the step to reflect that it is parameterized.
                    step_name = "{}_{}".format(step_exp.name, str(combo))
                    logger.debug("Step has been modified. Step '%s' renamed"
                                 " to '%s'", step_exp.name, step_name)
                    step_exp.name = step_name

                    # Set the workspace to the parameterized workspace
                    self.output.value = os.path.join(global_workspace,
                                                     str(combo))
                else:
                    # Otherwise, we know that this step is a joining node.
                    self.output.value = os.path.join(global_workspace)

                # Now we need to make sure we handle the dependencies.
                # We know the parent and the step name (whether it's modified
                # or not and is not _source). So now there's two cases:
                #   1. If the ExecutionGraph contains the parent name as it
                #      exists without parameterization, then we know we have
                #      a hub/joining node.
                #   2. If the ExecutionGraph does not have the parent node,
                #      then our next assumption is that it has a parameterized
                #      version of the parent. We need to check and make sure.
                #   3. Fall back third case... Abort. Something is not right.
                if step_exp.run["restart"]:
                    rlimit = self._restart_limit
                else:
                    rlimit = 0

                param_name = "{}_{}".format(parent, str(combo))
                if parent != SOURCE:
                    # If the parent node is not '_source', check.
                    if parent in dag.values:
                        # If the parent is in the dag, add the current step...
                        dag.add_step(step_exp.name, step_exp,
                                     self.output.value, rlimit)
                        # And its associated edge.
                        dag.add_edge(parent, step_exp.name)
                    elif param_name in dag.values:
                        # Find the index in the step for the dependency...
                        i = step_exp.run['depends'].index(parent)
                        # Sub it with parameterized dependency...
                        step_exp.run['depends'][i] = param_name
                        # Add the node and edge.
                        dag.add_step(step_exp.name, step_exp,
                                     self.output.value, rlimit)
                        dag.add_edge(param_name, step_exp.name)
                    else:
                        msg = "'{}' nor '{}' found in the ExecutionGraph. " \
                              "Unexpected error occurred." \
                              .format(parent, param_name)
                        logger.error(msg)
                        raise ValueError(msg)
                else:
                    # If the parent is source, then we can just execute it from
                    # '_source'.
                    dag.add_step(step_exp.name, step_exp, self.output.value,
                                 rlimit)
                    dag.add_edge(SOURCE, step_exp.name)

                # Go ahead and substitute in the output path and create the
                # workspace in the ExecutionGraph.
                create_parentdir(self.output.value)
                step_exp.__dict__ = apply_function(step_exp.__dict__,
                                                   self.output.substitute)

                # logging
                logger.debug("---------------- Modified --------------")
                logger.debug("Modified = %s", modified)
                logger.debug("step_exp = %s", step_exp.__dict__)
                logger.debug("----------------------------------------")

                # Reset the output path to the global_workspace.
                self.output.value = global_workspace
                logger.info(
                    "==================================================")

        return global_workspace, dag

    def stage(self):
        """
        Method that produces the expanded DAG representing the Study.

        Staging creates an ExecutionGraph based on the combinations generated
        by the ParameterGeneration object stored in an instance of a Study.
        The stage method also sets up individual working directories (or
        workspaces) for each node in the workflow that requires it.

        :returns: An ExecutionGraph object with the expanded workflow.
        """
        # If not set up, return None.
        if not self._issetup:
            msg = "Study {} is not set up for staging. Run setup before " \
                  "attempting to stage.".format(self.name)
            logger.error(msg)
            raise Exception(msg)

        # After substituting, we should start getting combinations and
        # iterating. Two options here:
        # 1. Just create a new DAG with the step names altered to reflect the
        #    parameters they use.
        # 2. Create a derived DAG that has look up tables for each node based
        #    parameters. This might reduce to the same as 1, but retains the
        #    same original naming. Though that doesn't matter since the actual
        #    object has the original name.
        # NOTE: fdinatal - 2/6/17: Looks like 1 is the easiest to get done,
        # going with that for now.
        # NOTE: fdinatal - 3/28/17: Revisiting this method.. my previous logic
        # was flawed.
        # NOTE: fdinatal - 5/17/17: There is the strong possibility this method
        # will need to be reworked some in the future. It likely won't need to
        # be a complete gutting of the method, but there may need to be logic
        # for different styles of launching since it's the ExecutionGraph that
        # will need to be formatted properly so that scripts get generated in
        # the appropriate fashion.

        # We have two cases:
        # 1. Parameterized workflows
        # 2. A linear, execute as specified workflow
        # NOTE: This scheme could be how we handle derived use cases.
        if self.parameters:
            return self._setup_parameterized()
        else:
            raise NotImplementedError()


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

        :param adapter: Instance of a ScriptAdapter interface.
        """
        if not isinstance(adapter, ScriptAdapter):
            msg = "ExecutionGraph adapters must be of type 'ScriptAdapter.'"
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
            to_be_scheduled, cmd_script, restart_script = \
                self._adapter.write_script(record.workspace, record.step)
            logger.info("Step -- %s\nScript: %s\nRestart: %s\nScheduled?: %s",
                        record.step.name, cmd_script, restart_script,
                        to_be_scheduled)
            record.to_be_scheduled = to_be_scheduled
            record.script = cmd_script
            record.restart_script = restart_script

    def _execute_local(self, step, path, cwd, env=None):
        """
        Execute a command locally.

        :param step: The StudyStep instance this submission is based on.
        :param path: Local path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param env: A dict containing a modified set of environment variables
        for execution.
        :returns: The return status of the executed command and PID.
        """
        logger.debug("cwd = %s", cwd)
        logger.debug("Script to execute: %s", path)
        p = Popen(path, shell=False, stdout=PIPE, stderr=PIPE, cwd=cwd,
                  env=env)
        pid = p.pid
        output, err = p.communicate()
        retcode = p.wait()

        if retcode == 0:
            logger.info("Execution returned status OK.")
            return SubmissionCode.OK, pid
        else:
            logger.warning("Execution returned an error: {}", err)
            return SubmissionCode.ERROR, pid

    def _execute_record(self, name, record, restart=False):
        """
        Execute a StepRecord.

        :param name: The name of the step to be executed.
        :param record: An instance of a _StepRecord class.
        :param restart: True if the record needs restarting, False otherwise.
        """
        num_restarts = 0    # Times this step has temporally restarted.
        retcode = None      # Execution return code.

        # While our submission needs to be submitted, keep trying:
        # 1. If the JobStatus is not OK.
        # 2. num_restarts is less than self._submission_attempts
        while retcode != SubmissionCode.OK and \
                num_restarts < self._submission_attempts:
            logger.info("Attempting submission of '%s' (attempt %d of %d)...",
                        name, num_restarts + 1, self._submission_attempts)

            # If the record needs scheduling, use self._adapter.
            # If the restart is specified, use the record restart script.
            if record.to_be_scheduled is True and restart is False:
                retcode, jobid = self._adapter.submit(
                    record.step,
                    record.script,
                    record.workspace)

            elif record.to_be_scheduled is True and restart is True:
                retcode, jobid = self._adapter.submit(
                    record.step,
                    record.restart_script,
                    record.workspace)

            # If the record does not need scheduling, run locally.
            # If the restart is specified, use the record restart script.
            elif record.to_be_scheduled is False and restart is False:
                retcode, jobid = self._execute_local(
                    record.step,
                    record.script,
                    record.workspace)

            elif record.to_be_scheduled is False and restart is True:
                retcode, jobid = self._execute_local(
                    record.step,
                    record.restart_script,
                    record.workspace)

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
                        path, parent = self.bfs_subtree(name)
                        for node in path:
                            self.failed_steps.add(node)
                            self.values[node].status = State.FAILED

                elif status == State.HWFAILURE:
                    # TODO: Need to make sure that we do this a finite number
                    # of times.
                    # Resubmit the cmd.
                    logger.warning("Hardware failure detected. Attempting to "
                                   "resubmit step '%s'.", name)
                    # We can just let the logic below handle submission with
                    # everything else.
                    ready_steps[name] = self.values[name]

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

        # Use the adapter to grab the job statuses.
        retcode, job_status = self._adapter.check_jobs(joblist)
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
