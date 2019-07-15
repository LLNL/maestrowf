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
This module is intended to test maestrowf.interfaces.script.localscriptadapter
module. It is setup to use nose or pytest to do that testing.

This was created to verify existing functionality of the ScriptAdapterFactory
as it was converted to dynamically load all ScriptAdapters using a namespace
plugin methodology.
"""
from maestrowf.interfaces.script.localscriptadapter import LocalScriptAdapter
from maestrowf.interfaces import ScriptAdapterFactory


def test_local_adapter():
    """
    Tests to verify that LocalScriptAdapter has the key property set to 'local'
    this is validate that existing specifications do not break.
    :return:
    """
    assert(LocalScriptAdapter.key == 'local')


def test_local_adapter_in_factory():
    """
    Testing to makes sure that the LocalScriptAdapter has been registered
    correctly in the ScriptAdapterFactory.
    :return:
    """
    saf = ScriptAdapterFactory
    assert(saf.factories[LocalScriptAdapter.key] == LocalScriptAdapter)
    assert(LocalScriptAdapter.key in ScriptAdapterFactory.get_valid_adapters())
    assert(ScriptAdapterFactory.get_adapter(LocalScriptAdapter.key) ==
           LocalScriptAdapter)
