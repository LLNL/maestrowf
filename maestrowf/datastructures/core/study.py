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
from hashlib import md5
import logging
import os
import pickle
import re
from types import MethodType
import yaml

from maestrowf.abstracts import PickleInterface
from maestrowf.datastructures.dag import DAG
from maestrowf.utils import apply_function, create_parentdir, make_safe_path
from .executiongraph import ExecutionGraph

LOGGER = logging.getLogger(__name__)
SOURCE = "_source"
WSREGEX = re.compile(
    r"\$\(([-!\$%\^&\*\(\)_\+\|~=`{}\[\]:;<>\?,\.\/\w]+)\.workspace\)"
)
ALL_COMBOS = re.compile(
    r"_\*|\*"
)


class StudyStep:
    """
    Class that represents the data and API for a single study step.

    This class is primarily a 1:1 mapping of a study step in the YAML spec in
    terms of data. The StudyStep's class API should capture all functions that
    a step can be expected to perform, including:

    * Applying a combination of parameters to itself.
    * Tests for equality and non-equality to check for changes.
    * Other -- WIP
    """

    def __init__(self):
        """Object that represents a single workflow step."""
        self._name = ""
        self.description = ""
        self.nickname = ""
        self.run = {
                        "cmd":              "",
                        "depends":          "",
                        "pre":              "",
                        "post":             "",
                        "restart":          "",
                        "nodes":            "",
                        "procs":            "",
                        "gpus":             "",
                        "cores per task":   "",
                        "walltime":         "",
                        "reservation":      ""
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

    @property
    def name(self):
        """
        Get the name to assign to a task for this step.

        :returns: A utf-8 formatted string of the task name.
        """
        if self.nickname:
            return self.nickname
        return self._name

    @name.setter
    def name(self, value):
        """
        Set the name of a StudyStep instance.

        :param value: A string value representing the name to give the step.
        """
        self._name = value

    @property
    def real_name(self):
        """
        Get the real name of the step (ignore nickname).

        :returns: A string of the true name of a StudyStep instance.
        """
        return self._name

    def __eq__(self, other):
        """
        Equality operator for the StudyStep class.

        :param other: Object to compare self to.
        : returns: True if other is equal to self, False otherwise.
        """
        if isinstance(other, self.__class__):
            # This works because the classes are currently interfaces over
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


class Study(DAG, PickleInterface):
    """
    Collection of high level objects to perform study construction.

    The Study class is part of the meat and potatoes of this whole package. A
    Study object is where the intersection of the major moving parts are
    collected. These moving parts include:

    * ParameterGenerator for getting combinations of user parameters
    * StudyEnvironment for managing and applying the environment to studies
    * Study flow, which is a DAG of the abstract workflow

    The class is responsible for a number of the major key steps in study setup
    as well. Those responsibilities include (but are not limited to):

    * Setting up the workspace where a simulation campaign will be run.
    * Applying the StudyEnvionment to the abstract flow DAG:
        * Creating the global workspace for a study.
        * Setting up the parameterized workspaces for each combination.
        * Acquiring dependencies as specified in the StudyEnvironment.

    * Intelligently constructing the expanded DAG to be able to:
        * Recognize when a step executes in a parameterized workspace
        * Recognize when a step executes in the global workspace

    * Expanding the abstract flow to the full set of specified parameters.

    Future functionality that makes sense to add here:

    * Metadata collection. If we're setting things up here, collect the
      general information. We might even want to venture to say that a set
      of directives may be useful so that they could be placed into
      Dependency classes as hooks for dumping that data automatically.
    * A way of packaging an instance of the class up into something that is
      easy to store in the ExecutionDAG class so that an API can be
      designed in whatever class ends up managing all of this to have
      machine learning applications pipe messages to spin up new studies
      using the same environment.
    """

    def __init__(self, name, description,
                 studyenv=None, parameters=None, steps=None, out_path="./"):
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
        self.environment = studyenv
        self.parameters = parameters
        self._out_path = out_path
        self._meta_path = os.path.join(out_path, "meta")

        LOGGER.debug("OUTPUT_PATH = %s", out_path)
        # Flag the study as not having been set up and add the source node.
        self._issetup = False
        self.is_configured = False
        self.add_node(SOURCE, None)

        # Settings for handling restarts and submission attempts.
        self._restart_limit = 0
        self._submission_attempts = 0
        self._use_tmp = False
        self._dry_run = False

        # Management structures
        # The workspace used by each step.
        self.workspaces = {SOURCE: self._out_path}
        # Parameter independent dependencies by step.
        self.hub_depends = {SOURCE: set()}
        # Other dependencies per step.
        self.depends = {SOURCE: set()}
        # Parameters that each step depends on.
        self.used_params = {SOURCE: set()}
        # Combinations seen per step.
        self.step_combos = {SOURCE: set()}

        # If the user specified a flow in the form of steps, copy those into
        # into the Study object.
        if steps:
            for step in steps:
                # Deep copy because it prevents modifications after the fact.
                self.add_step(step)

    @property
    def output_path(self):
        """
        Property method for the OUTPUT_PATH specified for the study.

        :returns: The string path stored in the OUTPUT_PATH variable.
        """
        return self._out_path

    def store_metadata(self):
        """Store metadata related to the study."""
        # Create the metadata directory.
        create_parentdir(self._meta_path)

        # Store the environment object in order to preserve it.
        path = os.path.join(self._meta_path, "study")
        create_parentdir(path)
        path = os.path.join(path, "env.pkl")
        with open(path, 'wb') as pkl:
            pickle.dump(self, pkl)

        # Construct other metadata related to study construction.
        _workspaces = {}
        for key, value in self.workspaces.items():
            if key == "_source":
                _workspaces[key] = value
            elif key in self.step_combos:
                _workspaces[key] = os.path.split(value)[-1]
            else:
                _workspaces[key] = \
                    os.path.sep.join(value.rsplit(os.path.sep)[-2:])

        # Construct relative paths for the combinations and nest them in the
        # same way as the step combinations dictionary.
        _step_combos = {}
        for key, value in self.step_combos.items():
            if key == SOURCE:
                _step_combos[key] = self.workspaces[key]
            elif not self.used_params[key]:
                _ws = self.workspaces[key]
                _step_combos[key] = {key: os.path.split(_ws)[-1]}
            else:
                _step_combos[key] = {}
                for combo in value:
                    _ws = self.workspaces[combo]
                    _step_combos[key][combo] = \
                        os.path.sep.join(_ws.rsplit(os.path.sep)[-2:])

        metadata = {
            "dependencies": self.depends,
            "hub_dependencies": self.hub_depends,
            "workspaces": _workspaces,
            "used_parameters": self.used_params,
            "step_combinations": _step_combos,
        }
        # Write out the study construction metadata.
        path = os.path.join(self._meta_path, "metadata.yaml")
        with open(path, "wb") as metafile:
            metafile.write(yaml.dump(metadata).encode("utf-8"))

        # Write out parameter metadata.
        metadata = self.parameters.get_metadata()
        path = os.path.join(self._meta_path, "parameters.yaml")
        with open(path, "wb") as metafile:
            metafile.write(yaml.dump(metadata).encode("utf-8"))

        # Write out environment metadata
        path = os.path.join(self._meta_path, "environment.yaml")
        with open(path, "wb") as metafile:
            metafile.write(yaml.dump(os.environ.copy()).encode("utf-8"))

    def load_metadata(self):
        """Load metadata for the study."""
        if not os.path.exists(self._meta_path):
            return

        path = os.path.join(self._meta_path, "study", "env.pkl")
        with open(path, 'rb') as pkl:
            env = pickle.load(pkl)

        if not isinstance(env, type(self)):
            msg = "Object loaded from {path} is of type {type}. Expected an" \
                  " object of type '{cls}.'".format(path=path, type=type(env),
                                                    cls=type(self))
            LOGGER.error(msg)
            raise TypeError(msg)

        metapath = os.path.join(self._meta_path, "metadata.yaml")
        with open(metapath, "rb") as metafile:
            metadata = yaml.load(metafile)

        self.depends = metadata["dependencies"]
        self.hub_depends = metadata["hub_dependencies"]
        self.workspaces = metadata["workspaces"]
        self.used_params = metadata["used_parameters"]
        self.step_combos = metadata["step_combinations"]

    def add_step(self, step):
        """
        Add a step to a study.

        For this helper to be most effective, it recommended to apply steps in
        the order that they will be encountered. The method attempts to be
        intelligent and make the intended edge based on the 'depends' entry in
        a step. When adding steps out of order it's recommended to just use the
        base class DAG functionality and manually make connections.

        :param step: A StudyStep instance to be added to the Study instance.
        """
        # Add the node to the DAG.
        self.add_node(step.real_name, step)
        LOGGER.info(
            "Adding step '%s' to study '%s'...", step.name, self.name)
        # Apply the environment to the incoming step.
        step.__dict__ = \
            apply_function(step.__dict__, self.environment.apply_environment)

        # If the step depends on a prior step, create an edge.
        if "depends" in step.run and step.run["depends"]:
            for dependency in step.run["depends"]:
                LOGGER.info("{0} is dependent on {1}. Creating edge ("
                            "{1}, {0})...".format(step.real_name, dependency))
                if "*" not in dependency:
                    self.add_edge(dependency, step.real_name)
                else:
                    self.add_edge(
                        re.sub(ALL_COMBOS, "", dependency),
                        step.real_name
                    )
        else:
            # Otherwise, if no other dependency, just execute the step.
            self.add_edge(SOURCE, step.real_name)

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

    def setup_workspace(self):
        """Set up the study's main workspace directory."""
        try:
            LOGGER.debug("Setting up study workspace in '%s'", self._out_path)
            create_parentdir(self._out_path)
        except Exception as e:
            LOGGER.error(e.args)
            return False

    def setup_environment(self):
        """Set up the environment by acquiring outside dependencies."""
        # Set up the environment if it hasn't been already.
        if not self.environment.is_set_up:
            LOGGER.debug("Environment is setting up.")
            self.environment.acquire_environment()

    def configure_study(self, submission_attempts=1, restart_limit=1,
                        throttle=0, use_tmp=False, hash_ws=False,
                        dry_run=False):
        """
        Perform initial configuration of a study. \

        The method is used for going through and actually acquiring each \
        dependency, substituting variables, sources and labels. \

        :param submission_attempts: Number of attempted submissions before \
        marking a step as failed. \
        :param restart_limit: Upper limit on the number of times a step with \
        a restart command can be resubmitted before it is considered failed. \
        :param throttle: The maximum number of in-progress jobs allowed. [0 \
        denotes no cap].\
        :param use_tmp: Boolean value specifying if the generated \
        ExecutionGraph dumps its information into a temporary directory. \
        :param dry_run: Boolean value that toggles dry run to just generate \
        study workspaces and scripts without execution or status checking. \
        :returns: True if the Study is successfully setup, False otherwise. \
        """

        self._submission_attempts = submission_attempts
        self._restart_limit = restart_limit
        self._submission_throttle = throttle
        self._use_tmp = use_tmp
        self._hash_ws = hash_ws
        self._dry_run = dry_run

        LOGGER.info(
            "\n------------------------------------------\n"
            "Submission attempts =       %d\n"
            "Submission restart limit =  %d\n"
            "Submission throttle limit = %d\n"
            "Use temporary directory =   %s\n"
            "Hash workspaces =           %s\n"
            "Dry run enabled =           %s\n"
            "Output path =               %s\n"
            "------------------------------------------",
            submission_attempts, restart_limit, throttle,
            use_tmp, hash_ws, dry_run, self._out_path
        )

        self.is_configured = True

    def _stage(self, dag):
        """
        Set up the ExecutionGraph of a parameterized study.

        :param throttle: Maximum number of in progress jobs allowed.
        :returns: The path to the study's global workspace and an expanded
            ExecutionGraph based on the parameters and parameterized workflow
            steps.
        """
        # Items to store that should be reset.
        LOGGER.info(
            "\n==================================================\n"
            "Constructing parameter study '%s'\n"
            "==================================================\n",
            self.name
        )

        # Topological sorted list of steps.
        t_sorted = self.topological_sort()

        # For each step, we need to assess what type of step it is.
        # So far we've seen five types of steps:
        # 1. Linear - The step uses no parameters, so we can add it as it is.
        # 2. Parameterized - The step uses or is dependent on steps that use
        # parameters.
        # 3. Parameter Independent - A step who only uses hub dependencies; or
        # phrased more concisely, is not directly dependent on the parameters
        # of a parent step but simply makes use of all of its combinations.
        # 4. Parameter Dependent - A step that may or may not be parameterized
        # itself, but whose combinations also depend on the combinations of its
        # parents.
        # 5. Parameterized and Parameter Independent - A step that is a combo
        # of #2 and #3 which requires the step to be expanded based on the
        # used parameters of the step, and then adding all parameterized
        # combinations of funneled steps.
        for step in t_sorted:
            LOGGER.info(
                "\n==================================================\n"
                "Processing step '%s'\n"
                "==================================================\n",
                step
            )
            # If we encounter SOURCE, just add it and continue.
            if step == SOURCE:
                LOGGER.info("Encountered '%s'. Adding and continuing.", SOURCE)
                dag.add_node(SOURCE, None)
                continue

            # We're dealing with an actual step. So we have to:
            # Update our management structures.
            node = self.values[step]
            self.hub_depends[step] = set()
            self.depends[step] = set()
            self.step_combos[step] = set()

            s_params = self.parameters.get_used_parameters(node)
            p_params = set()    # Used parameters excluding the current step.
            # Iterate through dependencies to update the p_params
            LOGGER.debug("\n*** Processing dependencies ***")
            for parent in node.run["depends"]:
                # If we have a dependency that is parameter independent, add
                # it to the hub dependency set.
                if "*" in parent:
                    LOGGER.debug("Found funnel dependency -- %s", parent)
                    self.hub_depends[step].add(re.sub(ALL_COMBOS, "", parent))
                else:
                    LOGGER.debug("Found dependency -- %s", parent)
                    # Otherwise, just note the parameters used by the step.
                    self.depends[step].add(parent)
                    p_params |= self.used_params[parent]

            # Search for workspace matches. These affect the expansion of a
            # node because they may use parameters. These are likely to cause
            # a node to fall into the 'Parameter Dependent' case.
            used_spaces = re.findall(
                WSREGEX, "{} {}".format(node.run["cmd"], node.run["restart"]))
            for ws in used_spaces:
                if ws not in self.used_params:
                    msg = "Workspace for '{}' is being used before it would" \
                          " be generated.".format(ws)
                    LOGGER.error(msg)
                    raise Exception(msg)

                # We have the case that if we're using a workspace of a step
                # that is a parameter independent dependency, we can skip it.
                # The parameters don't affect the combinations.
                if ws in self.hub_depends[step]:
                    LOGGER.info(
                        "'%s' parameter independent association found. "
                        "Skipping.", ws)
                    continue

                LOGGER.debug(
                    "Found workspace '%s' using parameters %s",
                    ws, self.used_params[ws])
                p_params |= self.used_params[ws]

            # Total parameters used for this step are the union of each parent
            # and the union of the parameters used by this step.
            self.used_params[step] = p_params | s_params

            # Check for a restart and set the rlimit accordingly.
            if node.run["restart"]:
                rlimit = self._restart_limit
            else:
                rlimit = 0

            # 1. The step and all its preceding parents use no parameters.
            if not self.used_params[step]:
                LOGGER.info(
                    "\n-------------------------------------------------\n"
                    "Adding step '%s' (No parameters used)\n"
                    "-------------------------------------------------\n",
                    step
                )
                # If we're not using any parameters at all, we do:
                # Copy the step and set to not modified.
                self.step_combos[step].add(step)

                workspace = make_safe_path(self._out_path, *[step])
                self.workspaces[step] = workspace
                LOGGER.debug("Workspace: %s", workspace)

                # NOTE: I don't think it's valid to have a specific workspace
                # since a step with no parameters operates at the global level.
                # NOTE: Opting to save the old command for provenence reasons.
                cmd = node.run["cmd"]
                r_cmd = node.run["restart"]
                LOGGER.info("Searching for workspaces...\ncmd = %s", cmd)
                for match in used_spaces:
                    LOGGER.info("Workspace found -- %s", match)
                    workspace_var = "$({}.workspace)".format(match)
                    if match in self.hub_depends[step]:
                        # If we're looking at a parameter independent match
                        # the workspace is the folder that contains all of
                        # the outputs of all combinations for the step.
                        ws = make_safe_path(self._out_path, *[match])
                        LOGGER.info("Found funnel workspace -- %s", ws)
                    else:
                        ws = self.workspaces[match]
                    cmd = cmd.replace(workspace_var, ws)
                    r_cmd = r_cmd.replace(workspace_var, ws)
                # We have to deepcopy the node, otherwise when we modify it
                # here, it's reflected in the ExecutionGraph.
                node = copy.deepcopy(node)
                node.run["cmd"] = cmd
                node.run["restart"] = r_cmd
                LOGGER.debug("New cmd = %s", cmd)
                LOGGER.debug("New restart = %s", r_cmd)
                dag.add_step(step, node, workspace, rlimit)

                if self.depends[step] or self.hub_depends[step]:
                    # So, because we don't have used parameters, we can just
                    # loop over the dependencies and add them.
                    LOGGER.debug("Processing regular dependencies.")
                    for parent in self.depends[step]:
                        LOGGER.info("Adding edge (%s, %s)...", parent, step)
                        dag.add_connection(parent, step)

                    # We can still have a case where we have steps that do
                    # funnel into this one even though this particular step
                    # is not parameterized.
                    LOGGER.debug("Processing hub dependencies.")
                    for parent in self.hub_depends[step]:
                        for item in self.step_combos[parent]:
                            LOGGER.info("Adding edge (%s, %s)...", item, step)
                            dag.add_connection(item, step)
                else:
                    # Otherwise, just add source since we're not dependent.
                    LOGGER.debug("Adding edge (%s, %s)...", SOURCE, step)
                    dag.add_connection(SOURCE, step)

            # 2. The step has used parameters.
            else:
                LOGGER.info(
                    "\n==================================================\n"
                    "Expanding step '%s'\n"
                    "==================================================\n"
                    "-------- Used Parameters --------\n"
                    "%s\n"
                    "---------------------------------",
                    step, self.used_params[step]
                )
                # Now we iterate over the combinations and expand the step.
                for combo in self.parameters:
                    LOGGER.info("\n**********************************\n"
                                "Combo [%s]\n"
                                "**********************************",
                                str(combo))
                    # Compute this step's combination name and workspace.
                    nickname = None
                    combo_str = combo.get_param_string(self.used_params[step])
                    # We must encode explicitly to utf-8
                    # combo_str = combo_str.encode("utf-8")
                    if self._hash_ws:
                        nickname = md5(combo_str.encode("utf-8")).hexdigest()
                        workspace = make_safe_path(
                                        self._out_path,
                                        *[step, nickname])
                    else:
                        workspace = \
                            make_safe_path(self._out_path, *[step, combo_str])
                        LOGGER.debug("Workspace: %s", workspace)
                    combo_str = "{}_{}".format(step, combo_str)
                    self.workspaces[combo_str] = workspace

                    # Check if the step combination has been processed.
                    if combo_str in self.step_combos:
                        continue
                    # Add this step to the combinations seen.
                    self.step_combos[step].add(combo_str)

                    modified, step_exp = node.apply_parameters(combo)
                    step_exp.name = combo_str
                    step_exp.nickname = nickname

                    # Substitute workspaces into the combination.
                    cmd = step_exp.run["cmd"]
                    r_cmd = step_exp.run["restart"]
                    LOGGER.info("Searching for workspaces...\ncmd = %s", cmd)
                    for match in used_spaces:
                        # Construct the workspace variable.
                        LOGGER.info("Workspace found -- %s", ws)
                        workspace_var = "$({}.workspace)".format(match)
                        if match in self.hub_depends[step]:
                            # If we're looking at a parameter independent match
                            # the workspace is the folder that contains all of
                            # the outputs of all combinations for the step.
                            ws = make_safe_path(self._out_path, *[match])
                            LOGGER.info("Found funnel workspace -- %s", ws)
                        elif not self.used_params[match]:
                            # If it's not a funneled dependency and the match
                            # is not parameterized, then the workspace is just
                            # the unparameterized match.
                            ws = self.workspaces[match]
                            LOGGER.info(
                                "Found unparameterized workspace -- %s", match)
                        else:
                            # Otherwise, we're dealing with a combination.
                            ws = "{}_{}".format(
                                match,
                                combo.get_param_string(self.used_params[match])
                            )
                            LOGGER.info(
                                "Found parameterized workspace -- %s", ws)
                            ws = self.workspaces[ws]

                        # Replace in both the command and restart command.
                        cmd = cmd.replace(workspace_var, ws)
                        r_cmd = r_cmd.replace(workspace_var, ws)
                    LOGGER.info("New cmd = %s", cmd)

                    step_exp.run["cmd"] = cmd
                    step_exp.run["restart"] = r_cmd
                    # Add to the step to the DAG.
                    dag.add_step(
                        step_exp.real_name, step_exp, workspace, rlimit,
                        params=combo.get_param_values(self.used_params[step]))

                    if self.depends[step] or self.hub_depends[step]:
                        # So, because we don't have used parameters, we can
                        # just loop over the dependencies and add them.
                        LOGGER.info("Processing regular dependencies.")
                        for p in self.depends[step]:
                            if self.used_params[p]:
                                p = "{}_{}".format(
                                    p,
                                    combo.get_param_string(self.used_params[p])
                                )
                            LOGGER.info(
                                "Adding edge (%s, %s)...", p, combo_str
                            )
                            dag.add_connection(p, combo_str)

                        # We can still have a case where we have steps that do
                        # funnel into this one even though this particular step
                        # is not parameterized.
                        LOGGER.debug("Processing hub dependencies.")
                        for parent in self.hub_depends[step]:
                            for item in self.step_combos[parent]:
                                LOGGER.info(
                                    "Adding edge (%s, %s)...", item, combo_str
                                )
                                dag.add_connection(item, combo_str)
                    else:
                        # Otherwise, just add source since we're not dependent.
                        LOGGER.debug(
                            "Adding edge (%s, %s)...", SOURCE, combo_str
                        )
                        dag.add_connection(SOURCE, combo_str)

        return dag

    def _stage_linear(self, dag):
        """
        Execute a linear workflow without parameters.

        :param throttle: Maximum number of in progress jobs allowed.
        :returns: The path to the study's global workspace and an
            ExecutionGraph based on linear steps in the study.
        """
        # For each step in the Study
        # Walk the study and add the steps to the ExecutionGraph.
        t_sorted = self.topological_sort()
        for step in t_sorted:
            # If we find the source node, we can just add it and continue.
            if step == SOURCE:
                LOGGER.debug("Source node found.")
                dag.add_node(SOURCE, None)
                continue

            # Initialize management structures.
            ws = make_safe_path(self._out_path, *[step])
            self.workspaces[step] = ws
            self.depends[step] = set()
            # Hub dependencies are not possible in linear studies. Empty set
            # for completion.
            self.hub_depends[step] = set()
            self.used_params[step] = set()
            self.step_combos[step] = set([step])

            node = self.values[step]
            # If the step has a restart cmd, set the limit.
            if node.run["restart"]:
                rlimit = self._restart_limit
            else:
                rlimit = 0

            cmd = node.run["cmd"]
            r_cmd = node.run["restart"]
            LOGGER.info("Searching for workspaces...\ncmd = %s", cmd)
            used_spaces = re.findall(WSREGEX, cmd)
            for match in used_spaces:
                # In this case we don't need to look for any parameters, or
                # combination dependent ("funnel") steps. It's a simple sub.
                LOGGER.info("Workspace found -- %s", match)
                workspace_var = "$({}.workspace)".format(match)
                ws = self.workspaces[match]
                cmd = cmd.replace(workspace_var, ws)
                r_cmd = r_cmd.replace(workspace_var, ws)
            node.run["cmd"] = cmd
            node.run["restart"] = r_cmd

            # Add the step
            dag.add_step(step, node, ws, rlimit)
            # If the node does not depend on any other steps, make it so that
            # if connects to SOURCE.
            if not node.run["depends"]:
                dag.add_connection(SOURCE, step)
            else:
                # In this case, since our step names are not parameterized,
                # and due to topological sort, we can guarantee that our
                # dependencies have been added. Go through and add each edge.
                for parent in node.run["depends"]:
                    self.depends[step].add(parent)
                    dag.add_connection(parent, step)

        return dag

    def stage(self):
        """
        Generate the execution graph for a Study.

        Staging creates an ExecutionGraph based on the combinations generated
        by the ParameterGeneration object stored in an instance of a Study.
        The stage method also sets up individual working directories (or
        workspaces) for each node in the workflow that requires it.

        :returns: An ExecutionGraph object with the expanded workflow.
        """
        # If the workspace doesn't exist, raise an exception.
        if not os.path.exists(self._out_path):
            msg = "Study {} is not set up for staging. Workspace does not " \
                  "exists (Output Dir = {}).".format(self.name, self._out_path)
            LOGGER.error(msg)
            raise Exception(msg)

        # If the environment isn't set up, raise an exception.
        if not self.environment.is_set_up:
            msg = "Study {} is not set up for staging. Environment is not " \
                  "set up. Aborting.".format(self.name)
            LOGGER.error(msg)
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

        # Construct ExecutionGraph
        dag = ExecutionGraph(
            submission_attempts=self._submission_attempts,
            submission_throttle=self._submission_throttle,
            use_tmp=self._use_tmp, dry_run=self._dry_run)
        dag.add_description(**self.description)
        dag.log_description()

        # Because we're working within a Study class whose steps have already
        # been verified to not contain a cycle, we can override the check for
        # the execution graph. Because the execution graph is constructed from
        # the study steps, it won't contain a cycle.
        def _pass_detect_cycle(self):
            pass

        dag.detect_cycle = MethodType(_pass_detect_cycle, dag)

        return self._out_path, self._stage(dag)
