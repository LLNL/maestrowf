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

"""Classes that represent the environment of a study."""

import logging
import os
import re

from maestrowf.abstracts import Dependency
from maestrowf.utils import start_process

logger = logging.getLogger(__name__)


class GitDependency(Dependency):
    """Environment GitDependency class for substituting a git dependency."""

    def __init__(self, name, value, path, token='$', **kwargs):
        """
        Initialize the GitDependency class.

        The GitDepedency represents a dependency that is stored in a user
        accessible remote repository that supports the git protocol. Each
        GitDependency acquires itself from its designated remote repository;
        otherwise, this class operates like the Variable class and
        represents substrings that can be present within String data that are
        meant to be replaced. The general format that such items take is
        generally expressed as '<token>(<name>)', and will be replaced
        with the value specified.

        Currently, the GitDependency class only supports three optional
        parameters: branch, hash, and tag. Each operate as their name specifies
        according to how they would be used in git. The class will acquire the
        specific repository in accordance with a specified optional (example:
        if a tag is specfied, the class will clone then checkout the tag). The
        only caveat to the optionals is that only one may be used at a time.

        :params name: String name that refers to a GitDependency instance.
        :params value: The URL (SSH or FTP) to the remote git repository.
        :params path: The local path where the copy of the repository is
            cloned to.
        :params token: String of expected character(s) that appear at the
            beginning of a substring representing the dependency variable.
        :params kwargs: Optional keyword arguments - Only valid optionals are
            "branch", "hash", and "tag".
        """
        # Required base information
        self.name = name
        self.url = value
        # If the path is a valid path that exists, get abspath
        if os.path.exists(path):
            self.path = os.path.abspath(path)
        else:
            # Otherwise, store it as it is.
            self.path = path

        self.token = token

        # Optional information
        self.hash = kwargs.pop("hash", "")
        self.tag = kwargs.pop("tag", "")
        self.branch = kwargs.pop("branch", "")

        self._verification("PathDependency initialized without complete "
                           " settings. Set required [name, value] before "
                           "calling methods.")
        self._is_acquired = False

    def get_var(self):
        """
        Get the variable representation of the dependency's name.

        :returns: String of the Dependencies's name in token form.
        """
        return "{}({})".format(self.token, self.name)

    def substitute(self, data):
        """
        Substitute the dependency's value for its notation.

        :param data: String to substitute dependency into.
        :returns: String with the dependency's name replaced with its value.
        """
        if not self._verify():
            error = "Ensure that all required fields (name, value)," \
                    "are populated and that value is a valid path."
            logger.exception(error)
            raise ValueError(error)

        path = os.path.join(self.path, self.name)
        logger.debug("%s: %s", self.get_var(),
                     data.replace(self.get_var(), path))
        return data.replace(self.get_var(), path)

    def acquire(self, substitutions=None):
        """
        Acquire the dependency specified by the PathDependency.

        The GitDependency will clone the remote repository specified by the
        instance's value to the local repository specified by path. If a commit
        hash is specified, acquire will attempt to rebase to the repository
        version described by the hash. Alternatively, if a tag is specfied
        acquire will attempt to checkout the version labeled by the tag.

        :param substitutions: List of Substitution objects that can be applied.
        """
        if self._is_acquired:
            return

        if not self._verify():
            error = "Ensure that all required fields (name, value, " \
                    "path), are populated and that value is a " \
                    "valid path."
            logger.error(error)
            raise ValueError(error)

        if substitutions:
            for substitution in substitutions:
                self.path = substitution.substitute(self.path)
                self.url = substitution.substitute(self.url)

        path = os.path.join(self.path, self.name)

        # Moved the path existence here because git doesn't actually return a
        # specific enough error code.
        if os.path.exists(path):
            msg = "Destination path '{}' already exists and is not an " \
                  "empty directory.".format(path)
            logger.error(msg)
            raise Exception(msg)

        logger.info("Checking for connectivity to '%s'", self.url)
        p = start_process(["git", "ls-remote", self.url], shell=False)
        p.communicate()
        if p.returncode != 0:
            msg = "Connectivity check failed. Check that you have " \
                "permissions to the specified repository, that the URL is " \
                "correct, and that you have network connectivity. (url = {})" \
                .format(self.url)
            logger.error(msg)
            raise RuntimeError(msg)
        logger.info("Connectivity achieved!")

        logger.info("Cloning '%s' from '%s'...", self.name, self.url)
        clone = start_process(["git", "clone", self.url, path], shell=False)
        clone.communicate()
        if clone.returncode != 0:
            msg = "Failed to acquire GitDependency named '{}'. Check " \
              "that repository URL ({}) and repository local path ({}) " \
              "are valid.".format(self.name, self.url, path)
            logger.error(msg)
            raise Exception(msg)

        if self.hash:
            logger.info("Checking out SHA1 hash '%s'...", self.hash)
            chkout = start_process(["git", "checkout", self.hash],
                                   cwd=path, shell=False)
            retcode = chkout.wait()

            if retcode != 0:
                msg = "Unable to checkout SHA1 hash '{}' for the repository" \
                      " located at {}." \
                      .format(self.hash, self.url)
                logger.error(msg)
                raise ValueError(msg)

        if self.tag:
            logger.info("Checking out git tag '%s'...", self.tag)
            tag = "tags/{}".format(self.tag)
            chkout = start_process(["git", "checkout", tag],
                                   cwd=path, shell=False)

            retcode = chkout.wait()

            if retcode != 0:
                msg = "Unable to checkout tag '{}' for the repository" \
                      " located at {}".format(self.tag, self.url)
                logger.error(msg)
                raise ValueError(msg)

        if self.branch:
            logger.info("Checking out git branch '%s'...", self.branch)
            chkout = start_process(["git", "checkout", self.branch],
                                   cwd=path, shell=False)

            retcode = chkout.wait()

            if retcode != 0:
                msg = "Unable to checkout branch '{}' for the repository" \
                      " located at {}".format(self.tag, self.url)
                logger.error(msg)
                raise ValueError(msg)

        if not os.path.exists(self.path):
            error = "The specified path '{}' does not exist.".format(self.name)
            logger.exception(error)
            raise ValueError(error)

        self._is_acquired = True

    def _verify(self):
        """
        Verify that the necessary Dependency fields are populated.

        :returns: True if Dependency is valid, False otherwise.
        """
        valid_param_pattern = re.compile(r"\w+")
        required = bool(re.search(valid_param_pattern, self.name) and
                        re.search(valid_param_pattern, self.url) and
                        re.search(valid_param_pattern, self.path) and
                        self.token)

        opt_args = set([self.branch, self.hash, self.tag])
        opt_args.discard("")
        if len(opt_args) > 1:
            msg = "A GitDependency cannot specify both a commit hash and " \
                  "release tag. Specify one or the other, but not both."
            logger.error(msg)
            raise ValueError(msg)
        elif self.hash:
            optional = bool(re.search(valid_param_pattern, self.hash))
        elif self.tag:
            optional = bool(re.search(valid_param_pattern, self.tag))
        elif self.branch:
            optional = bool(re.search(valid_param_pattern, self.branch))
        else:
            optional = True

        return required and optional

    def __str__(self):
        """
        Generate the string representation of the object.

        :returns: A string with the token form of the variable.
        """
        return str(self.get_var())
