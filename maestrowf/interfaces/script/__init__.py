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


from maestrowf.abstracts.containers import Record
from maestrowf.abstracts.enums import CancelCode, SubmissionCode


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

        :returns: A string representing the job identifer assigned by the
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
