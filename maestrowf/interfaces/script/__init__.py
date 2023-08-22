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

"""Module for interfaces that support various schedulers."""
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
import inspect
import logging
import pkgutil

from maestrowf.abstracts.interfaces.flux import FluxInterface
from maestrowf.abstracts.containers import Record
from maestrowf.abstracts.enums import CancelCode, SubmissionCode

LOGGER = logging.getLogger(__name__)


class SubmissionRecord(Record):
    """A container for data about return state upon scheduler submission."""

    def __init__(self, subcode, retcode, jobid=-1):
        """
        Initialize a new SubmissionRecord.

        :param jobid: The assigned job identifier for this record.
        :param retcode: The submission code returned by the scheduler submit.
        """
        super(SubmissionRecord, self).__init__()
        self._subcode = subcode

        if subcode == SubmissionCode.OK:
            # If we got an error, ignore the job identifier.
            self._info["jobid"] = jobid
        self._info["retcode"] = retcode

    @property
    def job_identifier(self):
        """
        Property for the job identifier for the record.

        :returns: A string representing the job identifier assigned by the
                  scheduler.
        """
        return self._info.get("jobid", None)

    @property
    def submission_code(self):
        """
        Property for submission state for the record.

        :returns: A SubmissionCode enum representing the state of the
                  submission call.
        """
        return self._subcode

    @property
    def return_code(self):
        """
        Property for the raw return code returned from submission.

        :returns: An integer representing the state of the raw return code
                  from submission.
        """
        return self._info["retcode"]

    def add_info(self, key, value):
        """
        Set additional informational key-value information.

        :param key: Record key identifying data.
        :param value: Data to be recorded.
        """
        self._info[key] = value


class CancellationRecord(Record):
    """A container for data returned from a scheduler cancellation call."""

    def __init__(self, cancel_status, retcode):
        """Initialize an empty CancellationRecord."""
        self._status = {
            CancelCode.OK:      set(),
            CancelCode.ERROR:   set(),
        }   # Map of cancellation status to job set.
        self._retcode = retcode
        self._cstatus = cancel_status

    def add_status(self, jobid, cancel_status):
        """
        Add the cancellation status for a single job to a record.

        :param jobid: Unique job identifier for the job status to be added.
        :param cancel_status: CancelCode designating how cancellation
                              terminated.
        """
        if not isinstance(cancel_status, CancelCode):
            raise TypeError(
                "Parameter 'cancel_code' must be of type 'CancelCode'. "
                "Received type '%s' instead.", type(cancel_status))
        self._status[cancel_status].add(jobid)

    @property
    def cancel_status(self):
        """Get the high level CancelCode status."""
        return self._cstatus

    @property
    def return_code(self):
        """Get the return code from the cancel command."""
        return self._retcode

    def lookup_status(self, cancel_status):
        """
        Find the cancellation status of the job identified by jid.

        :param cancel_status: The CancelCode to look up.
        :returns: Set of job identifiers that match the requested status.
        """
        return self._status.get(cancel_status, set())


class FluxFactory(object):
    """A factory for swapping out Flux's backend interface based on version."""

    latest = "0.49.0"

    def _iter_flux():
        """
        Based off of packaging.python.org loop over a namespace and find the
        modules. This has been adapted for this particular use case of loading
        all classes implementing FluxInterface loaded from all modules in
        maestrowf.interfaces.script._flux.
        :return: an iterable of the classes existing in the namespace
        """
        # get loader for the script adapter package
        loader = pkgutil.get_loader('maestrowf.interfaces.script._flux')
        # get all of the modules in the package
        mods = [(name, ispkg) for finder, name, ispkg in pkgutil.iter_modules(
            loader.load_module('maestrowf.interfaces.script._flux').__path__,
            loader.load_module(
                'maestrowf.interfaces.script._flux').__name__ + "."
            )
        ]
        cs = []
        for name, _ in mods:
            # get loader for every module
            m = pkgutil.get_loader(name).load_module(name)
            # get all classes that implement ScriptAdapter and are not abstract
            for n, cls in m.__dict__.items():
                if isinstance(cls, type) and \
                 issubclass(cls, FluxInterface) and \
                 not inspect.isabstract(cls):
                    cs.append(cls)
        return cs

    factories = {
       interface.key: interface for interface in _iter_flux()
    }

    @classmethod
    def get_interface(cls, interface_id):
        if interface_id.lower() not in cls.factories:
            msg = "Interface '{0}' not found. Specify a supported version " \
                  "of Flux or implement a new one mapping to the '{0}'" \
                  .format(str(interface_id))
            LOGGER.error(msg)
            raise Exception(msg)

        return cls.factories[interface_id]

    @classmethod
    def get_valid_interfaces(cls):
        return cls.factories.keys()

    @classmethod
    def get_latest_interface(cls):
        return cls.factories[cls.latest]
