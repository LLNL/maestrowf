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
from maestrowf.interfaces import ScriptAdapterFactory
from maestrowf.interfaces.script import LocalScriptAdapter, SlurmScriptAdapter, \
    FluxScriptAdapter, SpectrumFluxScriptAdapter


def test_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories is not None)


def test_get_valid_adapters():
    saf = ScriptAdapterFactory
    assert(saf.factories.keys() == ScriptAdapterFactory.get_valid_adapters())


def test_local_adapter_in_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories['local'] == LocalScriptAdapter)
    assert('local' in ScriptAdapterFactory.get_valid_adapters())
    assert(ScriptAdapterFactory.get_adapter('local') == LocalScriptAdapter)


def test_slurm_adapter_in_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories['slurm'] == SlurmScriptAdapter)
    assert('slurm' in ScriptAdapterFactory.get_valid_adapters())
    assert(ScriptAdapterFactory.get_adapter('slurm') == SlurmScriptAdapter)


def test_flux_adapter_in_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories['flux'] == FluxScriptAdapter)
    assert('flux' in ScriptAdapterFactory.get_valid_adapters())
    assert(ScriptAdapterFactory.get_adapter('flux') == FluxScriptAdapter)


def test_flux_spectrum_adapter_in_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories['flux-spectrum'] == SpectrumFluxScriptAdapter)
    assert('flux-spectrum' in ScriptAdapterFactory.get_valid_adapters())
    assert(ScriptAdapterFactory.get_adapter('flux-spectrum') == SpectrumFluxScriptAdapter)
