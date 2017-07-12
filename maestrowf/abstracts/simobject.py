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

"""The core building block class for study related classes."""


class SimObject(object):
    """
    A base class for objects that provides a basic API.

    The SimObject is an object meant to capture the very basic functionality
    that core classes and other closesly related classes should adhere to.
    The eventual goal of having this base class is to allow a study to be
    designed and written in Python code, which allows for those objects to
    return a basic dictionary form which could be used to map from one study
    specification, format, or otherwise to another. This basic functionality
    also allows for a study to be easier to write using standard formats such
    as YAML or JSON in order to keep record of how the studies were performed.
    """

    @classmethod
    def from_dict(cls, dictionary):
        """
        Method for populating a SimObject from a dictionary.

        :param cls: Class to be instantiated.
        :param dict: Dictionary containing attribute data.
        :return: Instance of cls.
        """
        instance = cls()
        for key, value in dictionary.items():
            instance.__dict__[key] = value

        return instance

    def to_dict(self):
        """Return a dictionary version of the SimObject."""
        return self.__dict__
