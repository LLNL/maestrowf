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

"""
The core data structures for starting up studies.

This module contains all of the core data structures that are needed for
constructing and representing studies and the moving parts that they require.
These moving parts include but are not limited to:

* Classes for representing the abstract flow of a study. These objects at
  their core are the Study and StudyStep classes that are used to construct
  a DAG for the flow.
* Classes that represent the items in a study's environment such as
  variables, scripts, and dependencies (paths, git repos, etc.)
* Classes for managing the environment and that know how to apply the
  environment to an abstract flow.
* A set of classes for managing parameters and generating combinations of
  parameters in a clean Pythonic way.
"""

from maestrowf.datastructures.core.executiongraph import ExecutionGraph
from maestrowf.datastructures.core.parameters import Combination, \
    ParameterGenerator
from maestrowf.datastructures.core.study import Study, StudyStep
from maestrowf.datastructures.core.studyenvironment import StudyEnvironment

__all__ = ("Combination", "ExecutionGraph", "ParameterGenerator", "Study",
           "StudyEnvironment", "StudyStep")
