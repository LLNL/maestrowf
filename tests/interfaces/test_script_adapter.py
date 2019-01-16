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
import maestrowf.interfaces.script
import pytest

from maestrowf.interfaces import ScriptAdapterFactory, iter_namespace
from maestrowf.interfaces.script.localscriptadapter import LocalScriptAdapter
from maestrowf.interfaces.script.slurmscriptadapter import SlurmScriptAdapter
from maestrowf.interfaces.script.fluxscriptadapter import FluxScriptAdapter, SpectrumFluxScriptAdapter


def test_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories is not None)


def test_get_valid_adapters():
    saf = ScriptAdapterFactory
    assert(saf.factories.keys() == ScriptAdapterFactory.get_valid_adapters())


def test_adapter_none_found():
    with pytest.raises(Exception):
        ScriptAdapterFactory.get_adapter('empty-adapter')
