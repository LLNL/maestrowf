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
This module is intended to test maestrowf.interfacesmodule. It is setup to
use nose or pytest to do that testing.

This was created to verify existing functionality of the ScriptAdapterFactory
as it was converted to dynamically load all ScriptAdapters using a namespace
plugin methodology.
"""
import os

import pytest

from maestrowf.interfaces import ScriptAdapterFactory
from maestrowf.datastructures.core import StudyStep

from rich.pretty import pprint


def test_factory():
    """
    Test to verify that the ScriptAdapterFactory loads correctly
    """
    saf = ScriptAdapterFactory
    assert(saf.factories is not None)


def test_get_valid_adapters():
    """
    Test to verify that the keys in the internal factory is the same set as
    the results from get_valid_adapters()
    """
    saf = ScriptAdapterFactory
    assert(sorted(saf.factories.keys()) == sorted(ScriptAdapterFactory.get_valid_adapters()))


def test_adapter_none_found():
    """
    Test to verify that an Exception is raised when an non-existing adapter
    is requested from the factory
    """
    with pytest.raises(Exception):
        ScriptAdapterFactory.get_adapter('empty-adapter')

def test_adapter_script_generator():
    """
    Tests script generation and launcher token replacement
    """
    test_step = StudyStep()
    test_step.name = 'test-step'
    test_step.description = 'script writer test'
    test_step.run = {
        'cmd': ['$(LAUNCHER) echo "Hello, $(NAME)!" > hello_world.txt',
                'sleep 5'],
        'procs': 1
    }
    pprint(test_step)

    batch_info = {
        'type': 'local_parallel',
        'proc_count': 4,
        'shell': '/bin/bash'
    }
    adapter = ScriptAdapterFactory.get_adapter(batch_info['type'])

    adapter2 = adapter(**batch_info)
    
    print(adapter2)
    adapter2.write_script(os.path.abspath('.'), test_step)

    assert(1 == None)
