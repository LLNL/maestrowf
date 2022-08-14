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

"""Module containing all things needed for a YAML Study Specification."""

from copy import deepcopy
import json
import logging
import os
import re
import yaml

import jsonschema

from maestrowf.abstracts import Specification
from maestrowf.datastructures.core import (
    ParameterGenerator,
    StudyEnvironment,
    StudyStep,
)
from maestrowf.datastructures import environment

logger = logging.getLogger(__name__)


class YAMLSpecification(Specification):
    """
    Class for loading and verifying a Study Specification.

    The Specification class provides an abstracted interface for constructing
    and managing studies. The Specification class makes use of a YAML file
    written as a representation of a whole study. The goal of this class is to
    provide an abstracted interface that makes use of the core concepts as
    presented in the maestrowf.datastructure.core package. The objectives for
    such a structure are three-fold:

    1. Present users who do not want a coding interface with a means to
    execute their studies without having to know the underlying details
    of the package itself. If the user learns the core concepts as
    presented by the YAML specification, the study should be able to be
    parsed and executed by the underlying data structures.
    2. Providing an abstract specification aids in presentation to users
    because it provides a concrete example of not only how to use the
    MaestroWF package as a whole, but as a very useful way to discuss
    the core concepts without actually having to dive into the code.
    3. Provides a "living and breathing" example of how to use the core
    structures to make a presentable interface for users. The YAML
    specification just so happens to be a textual representation, but it
    is an example of how you would use an interface (of whatever type)
    to construct the core structures and make use of them to run a
    study.
    """

    def __init__(self):
        """
        Class representing a study specification and associated methods.

        The Specification class contains all the information represented
        """
        self.path = ""
        self.description = {}
        self.environment = {}
        self.batch = {}
        self.study = []
        self.globals = {}

    @classmethod
    def load_specification(cls, path):
        """
        Load a study specification.

        :param path: Path to a study specification.
        :returns: A specification object containing the information from path.
        """
        logger.info("Loading specification -- path = %s", path)
        try:
            # Load the YAML spec from the file.
            with open(path, "r") as data:
                specification = cls.load_specification_from_stream(data)

        except Exception as e:
            logger.exception(e.args)
            raise e

        # Populate the path to the specification that populated this instance.
        specification.path = path
        return specification

    @classmethod
    def load_specification_from_stream(cls, stream):
        """
        Load a study specification.

        :param stream: Raw text stream to study YAML specification data.
        :returns: A specification object containing the information from the
                  passed stream.
        """

        try:
            spec = yaml.load(stream, yaml.FullLoader)
        except AttributeError:
            logger.warning(
                "*** PyYAML is using an unsafe version with a known "
                "load vulnerability. Please upgrade your installation "
                "to a more recent version! ***"
            )
            spec = yaml.load(stream)

        logger.debug("Loaded specification -- \n%s", spec["description"])
        specification = cls()
        specification.path = None
        specification.description = spec.pop("description", {})
        specification.environment = spec.pop(
            "env",
            {"variables": {}, "sources": [], "labels": {}, "dependencies": {}},
        )
        specification.batch = spec.pop("batch", {})
        specification.study = spec.pop("study", [])
        specification.globals = spec.pop("global.parameters", {})

        logger.debug("Specification object created. Verifying...")
        specification.verify()
        logger.debug("Returning verified specification.")
        return specification

    def verify(self):
        """Verify the whole specification."""

        # load the YAMLSpecification schema file
        dirpath = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(dirpath, "schemas")
        schema_path = os.path.join(schema_path, "yamlspecification.json")
        with open(schema_path, "r") as json_file:
            schemas = json.load(json_file)

        self.verify_description(schemas["DESCRIPTION"])
        self.verify_environment(schemas["ENV"])
        self.verify_study(schemas["STUDY_STEP"])
        self.verify_parameters(schemas["PARAM"])

        logger.debug(
            "Specification %s - Verified. No apparent issues.", self.name
        )

    def verify_description(self, schema):
        """
        Verify the description in the specification.

        The description is required to have both a name and a description. If
        either is missing, the specification is considered invalid.
        """
        # Verify that the top level structure contains a name, description
        # and study.
        # We're REQUIRING that user specify a name and description for the
        # study.

        # validate description against json schema
        YAMLSpecification.validate_schema(
            "description", self.description, schema
        )

        logger.debug("Study description verified -- \n%s", self.description)

    def _verify_variables(self):
        """
        Verify the variables section of env in a specification.

        The criteria for each variable is as follows:
            1. Each variable must have a name and value (non-empty strings)
            2. A variable name cannot be repeated.

        :returns: A set of keys encountered in the variables section.
        """
        keys_seen = set()
        if "variables" not in self.environment:
            return keys_seen
        for key, value in self.environment["variables"].items():
            logger.debug("Verifying %s...", key)
            if not key:
                msg = (
                    "All variables must have a valid name. Empty strings "
                    "are not allowed."
                )
                logger.error(msg)
                raise ValueError(msg)

            if isinstance(value, str) and not value:
                msg = (
                    "All variables must have a valid value. Empty strings "
                    "are not allowed."
                )
                logger.error(msg)
                raise ValueError(msg)

            if key in keys_seen:
                msg = (
                    "Variable name '{}' is already taken. All variable "
                    "names must be unique.".format(key)
                )
                logger.error(msg)
                raise ValueError(msg)

            keys_seen.add(key)

        return keys_seen

    def _verify_sources(self):
        """Verify the sources section of env in a specification."""
        # NOTE: We need to figure out what source represents and how to verify.
        pass

    def _verify_dependencies(self, keys_seen):
        """
        Verify the dependencies section of env in a specification.

        A dependency is required to have at least a name in all cases. Other
        required keys are entirely dependent on the type of dependency.

        :param keys_seen: A set of the keys seen in other parts of the
            specification.
        :returns: A set of variable names seen.
        """
        dep_types = ["path", "git", "spack"]

        if "dependencies" not in self.environment:
            return keys_seen

        # For each dependency type, run through the required keys and name.
        for dep_type in dep_types:
            if dep_type in self.environment["dependencies"]:
                for item in self.environment["dependencies"][dep_type]:
                    # Make sure that the "name" attribute is not taken.
                    # Because every dependency should be responsible for
                    # substituting itself into data, they are required to have
                    # a name field.
                    if item["name"] in keys_seen:
                        msg = (
                            "Variable name '{}' is already taken. All "
                            "variable names must be unique.".format(
                                item["name"]
                            )
                        )
                        logger.error(msg)
                        raise ValueError(msg)

                    keys_seen.add(item["name"])

        return keys_seen

    def verify_environment(self, schema):
        """Verify that the environment in a specification is valid."""
        # validate environment against json schema
        YAMLSpecification.validate_schema("env", self.environment, schema)
        # Verify the variables section of the specification.
        keys_seen = self._verify_variables()
        # Verify the sources section of the specification.
        self._verify_sources()
        # Verify the dependencies in the specification.
        self._verify_dependencies(keys_seen)

    def verify_study(self, schema):
        """Verify the each step of the study in the specification."""
        # The workflow must have at least one step in it, otherwise, it's
        # not a workflow...
        try:
            if not self.study:
                raise ValueError(
                    "A study specification MUST contain at least "
                    "one step in its workflow."
                )

            logger.debug(
                "Verified that a study block exists. -- verifying " "steps."
            )
            self._verify_steps(schema)

        except Exception as e:
            logger.exception(e.args)
            raise

    def _verify_steps(self, schema):
        """
        Verify each study step in the specification.

        A study step is required to have a name, description, and a command.
        If any are missing, the specification is considered invalid.
        """
        try:
            for step in self.study:
                # validate step against json schema
                YAMLSpecification.validate_schema(
                    "study step '{}'".format(step["name"]),
                    step,
                    schema,
                )

        except Exception as e:
            logger.exception(e.args)
            raise

        logger.debug("Verified steps")

    def verify_parameters(self, schema):
        """
        Verify the parameters section of the specification.

        Verify that (if globals exist) they conform to the following:
        Each parameter must have:

        1. values
        2. label(s)

        Conditions that must be satisfied for a collection of globals:

        1. All global names must be unique.
        2. Each list of values must be the same length.
        3. If the label is a list, its length must match the value length.
        """
        try:
            if self.globals:
                global_names = set()
                values_len = -1
                for name, value in self.globals.items():
                    # Check if the name is in the set
                    if name in global_names:
                        raise ValueError(
                            "Parameter '{}' is not unique in the "
                            "set of global parameters.".format(name)
                        )

                    # validate parameters against json schema
                    YAMLSpecification.validate_schema(
                        "global.params.{}".format(name),
                        value,
                        schema,
                    )

                    # If label is a list, check its length against values.
                    values = value["values"]
                    label = value["label"]
                    if isinstance(label, list):
                        if len(values) != len(label):
                            raise ValueError(
                                "Global parameter '{}' the "
                                "values length does not "
                                "match the label list length.".format(name)
                            )
                        if len(label) != len(set(label)):
                            raise ValueError(
                                "Global parameter '{}' the "
                                "label does not contain "
                                "unique labels.".format(name)
                            )
                    # Add the name to global parameters encountered, check if
                    # length of values is the same as previously encountered.
                    global_names.add(name)
                    # If length not set, set it and continue
                    if values_len == -1:
                        values_len = len(values)
                        continue

                    # Check length. Exception if doesn't match.
                    if len(values) != values_len:
                        raise ValueError(
                            "Global parameter '{}' is not the "
                            "same length as other parameters.".format(name)
                        )

        except Exception as e:
            logger.exception(e.args)
            raise

    @staticmethod
    def validate_schema(parent_key, instance, schema):
        """
        Given a parent key, an instance of a spec section, and a json schema
        for that section, validate the instance against the schema.
        """
        validator = jsonschema.Draft7Validator(schema)
        errors = validator.iter_errors(instance)
        for error in errors:
            path = ".".join(list(error.path))
            if error.validator == "additionalProperties":
                unrecognized = (
                    re.search(r"'.+'", error.message).group(0).strip("'")
                )
                raise jsonschema.ValidationError(
                    "Unrecognized key '{0}' found in {1}.".format(
                        unrecognized, parent_key
                    )
                )

            elif error.validator == "type":
                expected_type = (
                    re.search(r"is not of type '.+'", error.message)
                    .group(0)
                    .strip("is not of type ")
                    .strip("'")
                )
                raise jsonschema.ValidationError(
                    f"In {parent_key}, {path} must be of type "
                    f"'{expected_type}', but found "
                    f"'{type(instance[path]).__name__}'."
                )

            elif error.validator == "required":
                missing = re.search(r"'.+'", error.message)
                missing = missing.group(0)
                missing = missing.strip("'")
                raise jsonschema.ValidationError(
                    "Key '{0}' is missing from {1}.".format(
                        missing, parent_key
                    )
                )

            elif error.validator == "uniqueItems":
                raise jsonschema.ValidationError(
                    "Non-unique step names in {0}.run.depends.".format(
                        parent_key
                    )
                )

            elif error.validator == "minLength":
                raise jsonschema.ValidationError(
                    "In {0}, empty string found as value for {1}.".format(
                        parent_key, path
                    )
                )

            elif error.validator == "anyOf":
                path = ".".join(list(error.path))
                context_message = error.context[0].message
                context_message = re.sub(
                    r"'.+' ", "'{0}' ".format(path), context_message
                )
                raise jsonschema.ValidationError(
                    (
                        "The value '{0}' in field {1} of {2} is not of type "
                        "'{3}' or does not conform to the format '$(VARNAME)'."
                    ).format(
                        error.instance,
                        path,
                        parent_key,
                        error.validator_value[0]["type"],
                    )
                )

            else:
                raise ValueError("Validation error: " + error.message)

    @property
    def output_path(self):
        """
        Return the OUTPUT_PATH variable (if it exists).

        :returns: Returns OUTPUT_PATH if it exists, empty string otherwise.
        """
        if "variables" in self.environment:
            if "OUTPUT_PATH" in self.environment["variables"]:
                logger.debug(
                    "OUTPUT_PATH found in %s.", self.description["name"]
                )
                return self.environment["variables"]["OUTPUT_PATH"]
            else:
                return ""

    @property
    def name(self):
        """
        Getter for the name of a study specification.

        :returns: The name of the study described by the specification.
        """
        return self.description["name"]

    @name.setter
    def name(self, value):
        """
        Setter for the name of a study specification.

        :param value: String value representing the new name.
        """
        self.description["name"] = value

    @property
    def desc(self):
        """
        Getter for the description of a study specification.

        :returns: A string containing the description of the study
            specification.
        """
        return self.description["description"]

    @desc.setter
    def desc(self, value):
        """
        Setter for the description of a study specification.

        :param value: String value representing the new description.
        """
        self.description["description"] = value

    def get_study_environment(self):
        """
        Generate a StudyEnvironment object from the environment in the spec.

        :returns: A StudyEnvironment object with the data in the specification.
        """
        env = StudyEnvironment()
        if "variables" in self.environment:
            for key, value in self.environment["variables"].items():
                logger.debug("Key: %s, Value: %s", key, value)
                _ = environment.Variable(key, value)
                env.add(_)

        if "sources" in self.environment:
            for source in self.environment["sources"]:
                _ = environment.Script(source)
                env.add(_)

        if "labels" in self.environment:
            for key, value in self.environment["labels"].items():
                logger.debug("Key: %s, Value: %s", key, value)
                label = environment.Variable(key, value)
                env.add(label)

        if "dependencies" in self.environment:
            if "paths" in self.environment["dependencies"]:
                for path in self.environment["dependencies"]["paths"]:
                    _ = environment.PathDependency(path["name"], path["path"])
                    env.add(_)

            if "git" in self.environment["dependencies"]:
                for repo in self.environment["dependencies"]["git"]:
                    optionals = deepcopy(repo)
                    optionals.pop("name")
                    optionals.pop("url")
                    optionals.pop("path")
                    _ = environment.GitDependency(
                        repo["name"], repo["url"], repo["path"], **optionals
                    )
                    env.add(_)

        return env

    def get_parameters(self):
        """
        Generate a ParameterGenerator object from the global parameters.

        :returns: A ParameterGenerator with data from the specification.
        """
        params = ParameterGenerator()
        for key, value in self.globals.items():
            if "name" not in value:
                params.add_parameter(key, value["values"], value["label"])
            else:
                params.add_parameter(
                    key, value["values"], value["label"], value["name"]
                )

        return params

    def get_study_steps(self):
        """
        Generate a list of StudySteps from the study in the specification.

        :returns: A list of StudyStep objects.
        """
        steps = []
        for step in self.study:
            _ = StudyStep()
            _.name = step["name"]
            _.description = step["description"]
            for key, value in step["run"].items():
                _.run[key] = value
            steps.append(_)

        return steps
