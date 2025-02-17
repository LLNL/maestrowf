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
This module is intended to test maestrowf.interfaces.script.slurmscriptadapter
module. It is setup to use nose or pytest to do that testing.

This was created to verify existing functionality of the ScriptAdapterFactory
as it was converted to dynamically load all ScriptAdapters using a namespace
plugin methodology.
"""
import logging
import os
import re
from subprocess import CalledProcessError, check_output
import time

from maestrowf.abstracts.enums import State, JobStatusCode
from maestrowf.interfaces.script.slurmscriptadapter import SlurmScriptAdapter
from maestrowf.interfaces import ScriptAdapterFactory
from maestrowf.utils import start_process

import pytest

TESTLOGGER = logging.getLogger(__name__)

def test_slurm_adapter():
    """
    Tests to verify that SlurmScriptAdapter has the key property set to 'slurm'
    this is validate that existing specifications do not break.
    :return:
    """
    assert(SlurmScriptAdapter.key == 'slurm')


def test_slurm_adapter_in_factory():
    """
    Testing to makes sure that the SlurmScriptAdapter has been registered
    correctly in the ScriptAdapterFactory.
    :return:
    """
    saf = ScriptAdapterFactory
    # Make sure SlurmScriptAdapter is in the facotries object
    print(SlurmScriptAdapter)
    test_adapter = SlurmScriptAdapter
    # assert(saf.factories[SlurmScriptAdapter.key] is test_adapter)
    print(id(saf.factories[SlurmScriptAdapter.key]))
    print(id(SlurmScriptAdapter))
    assert(saf.factories[SlurmScriptAdapter.key] is SlurmScriptAdapter)
    # Make sure the SlurmScriptAdapter key is in the valid adapters
    assert(SlurmScriptAdapter.key in ScriptAdapterFactory.get_valid_adapters())
    # Make sure that get_adapter returns the SlurmScriptAdapter when asking
    # for it by key
    assert(ScriptAdapterFactory.get_adapter(SlurmScriptAdapter.key) ==
           SlurmScriptAdapter)


# Slurm fixtures for checking scheduler connectivity
@pytest.mark.sched_slurm
@pytest.fixture()
def slurm_test_jobs():
    """Spin up a couple sample jobs to test slurm connectivity"""

    # Archive the squeue/sacct formats so we can change them from defaults to verify
    # that user customizations don't break the adapter
    orig_sacct_fmt = os.getenv('SACCT_FORMAT')
    TESTLOGGER.warn("Original SACCT_FORMAT: %s", orig_sacct_fmt)
    orig_squeue_fmt = os.getenv('SQUEUE_FORMAT')
    TESTLOGGER.warn("Original SQUEUE_FORMAT: %s", orig_squeue_fmt)

    # Test out a users custom fmt here which had broken things previously (squeue)
    new_sacct_fmt = 'jobid,jobname,account,partition,nnodes,state,start,elapsed,timelimit,priority'
    new_squeue_fmt = '%.7i %.8u %.8a %.9P %.5D %.2t %.19S %.8M %.10l %10Q'
    
    os.environ['SACCT_FORMAT'] = new_sacct_fmt
    os.environ['SQUEUE_FORMAT'] = new_squeue_fmt
    TESTLOGGER.warn("Override SACCT_FORMAT: %s", os.environ['SACCT_FORMAT'])
    TESTLOGGER.warn("Override SQUEUE_FORMAT: %s", os.environ['SQUEUE_FORMAT'])
    
    jobids = []
    test_cmds = ["echo 'Test Job {}';srun -n1 sleep 60".format(idx) for idx in range(1)]
    for cmd in test_cmds:
        p = start_process(['sbatch', f'--wrap={cmd}', '-n', '1'], #.format(test_cmd=cmd)],
                          cwd=os.getcwd(),
                          env=os.environ)
        output, err = p.communicate()
        retcode = p.wait()

        if retcode == 0:
            jobids.append(re.search('[0-9]+', output).group(0))
        else:
            print(f'Error submitting job. retcode: {retcode}, output: {output}, err: {err}')

    yield jobids

    # Cleanup   (NOTE: want to also try cancelling jobs here or just let them run out?)
    if orig_sacct_fmt:
        os.environ['SACCT_FORMAT'] = orig_sacct_fmt
    else:
        os.environ.pop('SACCT_FORMAT')

    if orig_squeue_fmt:
        os.environ['SQUEUE_FORMAT'] = orig_squeue_fmt
    else:
        os.environ.pop('SQUEUE_FORMAT')

    TESTLOGGER.warn("Reverted SACCT_FORMAT: %s", os.getenv('SACCT_FORMAT'))
    TESTLOGGER.warn("Reverted SQUEUE_FORMAT: %s", os.getenv('SQUEUE_FORMAT'))

    TESTLOGGER.warn("Cleaning up slurm output logs")
    max_tries = 12
    attempt = 0

    slurm_adapter = ScriptAdapterFactory.get_adapter(SlurmScriptAdapter.key)(
        host='dummy_host',
        bank='dummy_bank',
        queue='dummy_queue',
        nodes=''
    )
    failed_jobstatus_codes = [JobStatusCode.ERROR]
    live_states = [State.PENDING, State.FINISHING, State.RUNNING]
    jobs_running = {jobid: True for jobid in jobids}
    jobs_still_running = True
    while attempt < max_tries and jobs_still_running:
        time.sleep(5)  # do one extra just in case it sticks in CG state
        for jobid in jobids:
            squeue_cmd = f'squeue -j {jobid} --start -O "dependency,reason"'
            try:
                job_info = check_output(squeue_cmd, shell=True).decode('utf-8').splitlines()
                if job_info[1]:
                    TESTLOGGER.warn("Job %s found in squeue: %s", jobid, job_info)
                    jobs_running[jobid] = True

            except CalledProcessError:
                jobs_running[jobid] = False  # non-zero ret from squeue/couldn't find job
            except IndexError:
                jobs_running[jobid] = False  # no jobs in squeues' output

        slurm_adapter.cancel_jobs([jobid for jobid, job_is_running in jobs_running.items() if job_is_running])
        jobs_still_running = any([job_is_running for jobid, job_is_running in jobs_running.items()])
        attempt += 1

    # Now that jobs aren't still running we can remove the log files
    for jobid in jobids:
        slurm_log_file = os.path.abspath(f'slurm-{jobid}.out')
        try:
            os.remove(slurm_log_file)
            TESTLOGGER.warn("Removed slurm log for jobid %s", str(jobid))
        except FileNotFoundError as fnfe:
            TESTLOGGER.error("Could not find '%s' to delete it", slurm_log_file, exc_info=True)
            TESTLOGGER.error("Available files in cwd: %s", ', '.join(list(os.listdir())))


@pytest.mark.sched_slurm
def test_slurm_check(slurm_test_jobs, caplog):
    jobids = slurm_test_jobs
    caplog.set_level(logging.DEBUG)

    TESTLOGGER.warn("SACCT_FORMAT = %s", os.environ['SACCT_FORMAT'])
    TESTLOGGER.warn("SQUEUE_FORMAT = %s", os.environ['SQUEUE_FORMAT'])

    slurm_adapter = ScriptAdapterFactory.get_adapter(SlurmScriptAdapter.key)(
        host='dummy_host',
        bank='dummy_bank',
        queue='dummy_queue',
        nodes=''
    )
    failed_jobstatus_codes = [JobStatusCode.ERROR]
    failed_states = [State.FAILED, State.HWFAILURE]

    status_dict = {jobid: None for jobid in jobids}
    job_status_squeue = slurm_adapter._check_jobs_squeue(jobids, status_dict)

    TESTLOGGER.warn("Testing squeue job status code: %s", job_status_squeue[0])
    assert job_status_squeue[0] in JobStatusCode
    assert job_status_squeue[0] not in failed_jobstatus_codes

    TESTLOGGER.warn("Testing squeue statuses: %s", job_status_squeue[1])
    assert job_status_squeue[1]
    for jobid, jobstate in job_status_squeue[1].items():
        assert jobstate not in failed_states and jobstate in State

    # NOTE: sacct output is often blank with shorter sleep times. Maybe smarter
    #       handling with auto retries if sacct empty but squeue is fine?
    time.sleep(5)
    status_dict = {jobid: None for jobid in jobids}
    job_status_sacct = slurm_adapter._check_jobs_sacct(jobids, status_dict)

    TESTLOGGER.warn("Testing sacct job status code: %s", job_status_sacct[0])
    assert job_status_sacct[0] in JobStatusCode
    assert job_status_sacct[0] not in failed_jobstatus_codes

    TESTLOGGER.warn("Testing sacct statuses: %s", job_status_sacct[1])
    assert job_status_sacct[1]  # Make sure it's not empty
    for jobid, jobstate in job_status_sacct[1].items():
        assert jobstate         # Catch none with better err msg
        assert jobstate not in failed_states and jobstate in State


@pytest.mark.sched_slurm
def test_slurm_cancel(slurm_test_jobs, caplog):
    jobids = slurm_test_jobs

    TESTLOGGER.warn("SACCT_FORMAT = %s", os.environ['SACCT_FORMAT'])
    TESTLOGGER.warn("SQUEUE_FORMAT = %s", os.environ['SQUEUE_FORMAT'])

    slurm_adapter = ScriptAdapterFactory.get_adapter(SlurmScriptAdapter.key)(
        host='dummy_host',
        bank='dummy_bank',
        queue='dummy_queue',
        nodes=''
    )
    failed_jobstatus_codes = [JobStatusCode.ERROR]

    time.sleep(5)               # Let it run for a bit to actually generate log files
    slurm_adapter.cancel_jobs(jobids)

    time.sleep(5)               # Give it time to avoid catching finishing/cg state
    jobstatcode, job_status = slurm_adapter.check_jobs(jobids)

    TESTLOGGER.warn("Looking for cancelled job states for jobids '%s'",
                    ', '.join([str(jid) for jid in jobids]))

    TESTLOGGER.warn("Testing job status code: %s", jobstatcode)
    assert jobstatcode in JobStatusCode
    assert jobstatcode not in failed_jobstatus_codes

    # Note: what about finishing?  catch that and retry until it changes and
    # then look for cancelled?
    for jobid, jobstate in job_status.items():
        assert jobstate == State.CANCELLED
