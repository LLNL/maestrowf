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

from abc import ABCMeta, abstractmethod, abstractproperty
import six

from . import abstractclassmethod


@six.add_metaclass(ABCMeta)
class Specification:
    """Abstract class for loading and verifying a Study Specification"""

    @abstractclassmethod
    def load_specification(cls, path):
        """Method for loading a study specification from a file.

        Args:
          path: Path to a study specification.

        Returns:
          A specification object containing the information loaded
          from path.

        """

    @abstractclassmethod
    def load_specification_from_stream(cls, stream):
        """Method for loading a study specification from a stream.

        Args:
          stream: Raw text stream containing specification data.

        Returns:
          A specification object containing the information in string.

        """

    @abstractmethod
    def verify(self):
        """Verify the whole specification."""

    @abstractmethod
    def get_study_environment(self):
        """Generate a StudyEnvironment object from the environment in the spec.

        Args:

        Returns:
          A StudyEnvironment object with the data in the specification.

        """

    @abstractmethod
    def get_parameters(self):
        """Generate a ParameterGenerator object from the global parameters.

        Args:

        Returns:
          A ParameterGenerator with data from the specification.

        """

    @abstractmethod
    def get_study_steps(self):
        """Generate a list of StudySteps from the study in the specification.

        Args:

        Returns:
          A list of StudyStep objects.

        """

    @abstractproperty
    def output_path(self):
        """Return the OUTPUT_PATH variable (if it exists).

        Args:

        Returns:
          Returns OUTPUT_PATH if it exists, empty string otherwise.

        """

    @abstractproperty
    def name(self):
        """Getter for the name of a study specification.

        Args:

        Returns:
          The name of the study described by the specification.

        """

    @name.setter
    def name(self, value):
        """Setter for the name of a study specification.

        Args:
          value: String value representing the new name.

        Returns:

        """

    @abstractproperty
    def desc(self):
        """Getter for the description of a study specification.

        Args:

        Returns:
          A string containing the description of the study
          specification.

        """

    @desc.setter
    def desc(self, value):
        """Setter for the description of a study specification.

        Args:
          value: String value representing the new description.

        Returns:

        """
