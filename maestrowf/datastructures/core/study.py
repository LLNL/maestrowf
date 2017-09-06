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
import logging
import os
import re
import time

from maestrowf.abstracts import SimObject
from maestrowf.datastructures.core import ExecutionGraph
from maestrowf.datastructures.dag import DAG
from maestrowf.datastructures.environment import Variable
from maestrowf.utils import apply_function, create_parentdir

logger = logging.getLogger(__name__)
SOURCE = "_source"
WSREGEX = re.compile(
    r"\$\(([-!\$%\^&\*\(\)_\+\|~=`{}\[\]:;<>\?,\.\/\w]+)\.workspace\)"
)


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
        out_name = "{}_{}".format(
            self.name.replace(" ", "_"),
            time.strftime("%Y%m%d-%H%M%S")
        )
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

        # Rework begins here:
        # First step, we need to map each workflow step to the parameters that
        # they actually use -- and only the parameters used. This setup will
        # make it so that workflows can be constructed with implicit stages.
        # That's to say that if a step only requires a subset of parameters,
        # we only need to run the set of combinations dictated by that subset.
        # NOTE: We're going to need to make a way for users to access the
        # workspaces of other steps. With this rework we won't be able to
        # assume that every directory has all parameters on it.
        used_params = {}
        workspaces = {}
        for parent, step, node in self.walk_study():
            # Source doesn't matter -- ignore it.
            if step == SOURCE:
                continue

            # Otherwise, we have a valid key.
            # We need to collect used parameters for two things:
            # 1. Collect the used parameters for the current step.
            # 2. Get the used parameters for the parent step.
            # The logic here is that the used parameters are going to be the
            # union of the used parameters for this step and ALL parent steps.
            # If we keep including the step's parent parameters, we will simply
            # carry parent parameters recursively.
            step_params = self.parameters.get_used_parameters(node)
            if parent != SOURCE:
                step_params |= used_params[parent]
            used_params[step] = step_params

        logger.debug("Used Parameters - \n%s", used_params)

        # Secondly, we need to now iterate over all combinations for each step
        # and simply apply the combination. We can then add the name to the
        # expanded map using only the parameters that we discovered above.
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
                # Due to the rework, we now can get the parameters used. We no
                # longer have to blindly apply the parameters. In fact, better
                # if we don't know. We have to see if the name exists in the
                # DAG first. If it does we can skip the step. Otherwise, apply
                # and add.
                if used_params[step]:
                    logger.debug("Used parameters %s", used_params[step])
                    # Apply the used parameters to the step.
                    modified, step_exp = node.apply_parameters(combo)
                    # Name the step based on the parameters used.
                    combo_str = combo.get_param_string(used_params[step])
                    step_name = "{}_{}".format(step_exp.name, combo_str)
                    logger.debug("Step has been modified. Step '%s' renamed"
                                 " to '%s'", step_exp.name, step_name)
                    step_exp.name = step_name
                    logger.debug("Resulting step name: %s", step_name)

                    # Set the workspace to the parameterized workspace
                    self.output.value = os.path.join(global_workspace,
                                                     combo_str)

                    # We now should account for varying workspace locations.
                    # Search for the use of workspaces in the command line so
                    # that we can go ahead and fill in the appropriate space
                    # for this combination.
                    cmd = step_exp.run["cmd"]
                    used_spaces = re.findall(WSREGEX, cmd)
                    for match in used_spaces:
                        logger.debug("Workspace found -- %s", match)
                        # Append the parameters that the step uses matching the
                        # current combo.
                        combo_str = combo.get_param_string(used_params[match])
                        logger.debug("Combo str -- %s", combo_str)
                        if combo_str:
                            _ = "{}_{}".format(match, combo_str)
                        else:
                            _ = match
                        # Replace the workspace tag in the command.
                        workspace_var = "$({}.workspace)".format(match)
                        cmd = cmd.replace(workspace_var, workspaces[_])
                        logger.debug("New cmd -- %s", cmd)
                    step_exp.run["cmd"] = cmd
                else:
                    # Otherwise, we know that this step is a joining node.
                    step_exp = copy.deepcopy(node)
                    modified = False
                    logger.debug("No parameters found. Resulting name %s",
                                 step_exp.name)
                    self.output.value = os.path.join(global_workspace)

                # Add the workspace name to the map of workspaces.
                workspaces[step_exp.name] = self.output.value

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

                if parent != SOURCE:
                    # With the rework, we now need to check the parent's used
                    # parmeters.
                    combo_str = combo.get_param_string(used_params[parent])
                    param_name = "{}_{}".format(parent, combo_str)
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

    def _setup_linear(self):
        """
        Execute a linear workflow without parameters.

        :returns: The path to the study's global workspace and an
        ExecutionGraph based on linear steps in the study.
        """
        # Construct ExecutionGraph
        dag = ExecutionGraph()
        dag.add_description(**self.description)
        # Items to store that should be reset.
        logger.info("==================================================")
        logger.info("Constructing linear study '%s'", self.name)
        logger.info("==================================================")

        # For each step in the Study
        # Walk the study and add the steps to the ExecutionGraph.
        for parent, step, node in self.walk_study():
            # If we find the source node, we can just add it and continue.
            if step == SOURCE:
                logger.debug("Source node found.")
                dag.add_node(SOURCE, None)
                continue

            # If the step has a restart cmd, set the limit.
            if node.run["restart"]:
                rlimit = self._restart_limit
            else:
                rlimit = 0

            # Add the step
            dag.add_step(step, node, self.output.value, rlimit)
            dag.add_edge(parent, step)

        return self.output.value, dag

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
            return self._setup_linear()
