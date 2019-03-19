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
from maestrowf.abstracts.enums import SubmissionCode


class SubmissionRecord(Record):
    """A container for data about return state upon scheduler submission."""

    def __init__(self, jobid, subcode, retcode):
        """
        Initialize a new SubmissionRecord.

        :param jobid: The assigned job identifier for this record.
        :param retcode: The submission code returned by the scheduler submit.
        """
        self._subcode = subcode
        self._info = {}

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
