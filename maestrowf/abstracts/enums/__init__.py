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

"""Package for providing enumerations for interfaces"""
from __future__ import annotations
from enum import Enum

__all__ = (
    "JobStatusCode", "State", "SubmissionCode", "StepUrgency", "StudyStatus"
)


class SubmissionCode(Enum):
    OK = 0
    ERROR = 1


class CancelCode(Enum):
    OK = 0
    ERROR = 1


class JobStatusCode(Enum):
    OK = 0
    NOJOBS = 1
    ERROR = 2


class State(Enum):
    """Workflow step state enumeration."""

    INITIALIZED = 0
    PENDING = 1
    WAITING = 2
    RUNNING = 3
    FINISHING = 4
    FINISHED = 5
    QUEUED = 6
    FAILED = 7
    INCOMPLETE = 8
    HWFAILURE = 9
    TIMEDOUT = 10
    UNKNOWN = 11
    CANCELLED = 12
    NOTFOUND = 13
    DRYRUN = 14


class StudyStatus(Enum):
    """Workflow status enumeration"""
    FINISHED = 0   # The Study has finished successfully, all steps ran
    RUNNING = 1    # The Study is currently running
    FAILURE = 2    # The Study has finished, but 1 or more steps failed
    CANCELLED = 3  # The Study has finished, but was cancelled


class StepUrgency(Enum):
    """Scheduler priority for submitted jobs"""
    HELD = 0
    MINIMAL = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    EXPEDITE = 5

    @classmethod
    def from_str(cls, urgency: str) -> StepUrgency:
        _urgency = urgency.lower()

        if _urgency == "held":
            return cls.HELD
        if _urgency == "minimal":
            return cls.MINIMAL
        if _urgency == "medium":
            return cls.MEDIUM
        if _urgency == "high":
            return cls.HIGH
        if _urgency == "expedite":
            return cls.EXPEDITE

        raise ValueError(f"Urgency '{urgency}' not valid.")
