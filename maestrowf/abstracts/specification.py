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

from maestrowf.abstracts import abstractclassmethod


@six.add_metaclass(ABCMeta)
class Specification(object):
    """
    Abstract class for loading and verifying a Study Specification
    """

    @abstractclassmethod
    def load_specification(cls, path):
        """
        Method for loading a study specification.

        :param path: Path to a study specification.
        :returns: A specification object containing the information from path.
        """
        pass

    @abstractmethod
    def verify(self):
        """
        Verify the whole specification.
        """
        pass

    @abstractmethod
    def get_study_environment(self):
        """
        Generate a StudyEnvironment object from the environment in the spec.

        :returns: A StudyEnvironment object with the data in the specification.
        """
        pass

    @abstractmethod
    def get_parameters(self):
        """
        Generate a ParameterGenerator object from the global parameters.

        :returns: A ParameterGenerator with data from the specification.
        """
        pass

    @abstractmethod
    def get_study_steps(self):
        """
        Generate a list of StudySteps from the study in the specification.

        :returns: A list of StudyStep objects.
        """
        pass

    @abstractproperty
    def output_path(self):
        """
        Return the OUTPUT_PATH variable (if it exists).

        :returns: Returns OUTPUT_PATH if it exists, empty string otherwise.
        """
        pass

    @abstractproperty
    def name(self):
        """
        Getter for the name of a study specification.

        :returns: The name of the study described by the specification.
        """
        pass

    @name.setter
    def name(self, value):
        """
        Setter for the name of a study specification.

        :param value: String value representing the new name.
        """
        pass

    @abstractproperty
    def desc(self):
        """
        Getter for the description of a study specification.

        :returns: A string containing the description of the study
            specification.
        """
        pass

    @desc.setter
    def desc(self, value):
        """
        Setter for the description of a study specification.

        :param value: String value representing the new description.
        """
        pass
