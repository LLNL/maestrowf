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
from maestrowf.interfaces.script.fluxscriptadapter import FluxScriptAdapter, SpectrumFluxScriptAdapter
from maestrowf.interfaces import ScriptAdapterFactory


def test_flux_adapter():
    assert(FluxScriptAdapter.key == 'flux')


def test_flux_spectrum_adapter():
    assert(SpectrumFluxScriptAdapter.key == 'flux-spectrum')


def test_flux_adapter_in_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories[FluxScriptAdapter.key] == FluxScriptAdapter)
    assert(FluxScriptAdapter.key in ScriptAdapterFactory.get_valid_adapters())
    assert(ScriptAdapterFactory.get_adapter(FluxScriptAdapter.key) == FluxScriptAdapter)


def test_flux_spectrum_adapter_in_factory():
    saf = ScriptAdapterFactory
    assert(saf.factories[SpectrumFluxScriptAdapter.key] == SpectrumFluxScriptAdapter)
    assert(SpectrumFluxScriptAdapter.key in ScriptAdapterFactory.get_valid_adapters())
    assert(ScriptAdapterFactory.get_adapter(SpectrumFluxScriptAdapter.key) == SpectrumFluxScriptAdapter)
