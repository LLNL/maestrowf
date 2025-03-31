#!/usr/bin/env python3
import argparse
import math
from pathlib import Path
import random
import sys
import tempfile
import time

import cProfile
import pstats
import timeit

from maestrowf.interfaces.script.fluxscriptadapter import FluxScriptAdapter
from maestrowf.interfaces.script import SubmissionRecord
from maestrowf.datastructures.core.study import StudyStep

from flux.job.executor import (
    FluxExecutor,
    FluxExecutorFuture
)

from rich.pretty import pprint

RUN_BASE = {
    "cmd":              "",
    "restart":          "",
    "nodes":            "",
    "procs":            "",
    "gpus":             "",
    "cores per task":   "",
    "walltime":         "",
}

RUN_DEFAULTS = {
    "procs": 1,
    "nodes": 1,
    "gpus": 0,
    "cores per task": 1,
}


def dummy_step_builder(task_id, sleep_time, walltime, procs=None, nodes=None, gpus=None, cores_per_task=None):
    cmd = """echo "Task: {task}"
sleep {sleep_time}"""
    rundict = {}
    rundict['restart'] = ""
    rundict['nested'] = True
    for key in RUN_BASE:
        if not procs:
            rundict['procs'] = RUN_DEFAULTS['procs']
        else:
            rundict['procs'] = procs
        if not nodes:
            rundict['nodes'] = RUN_DEFAULTS['nodes']
        else:
            rundict['nodes'] = nodes
        if not gpus:
            rundict['gpus'] = RUN_DEFAULTS['gpus']
        else:
            rundict['gpus'] = gpus

        if not cores_per_task:
            rundict['cores per task'] = RUN_DEFAULTS['cores per task']
        else:
            rundict['cores per task'] = cores_per_task

        rundict['walltime'] = walltime
        rundict['cmd'] = cmd.format(task=task_id, sleep_time=sleep_time)

    job_step = StudyStep()
    # job_step.name = "dummy_task"
    job_step.name = f"dummy_task_{task_id}_sleep_{sleep_time}"
    job_step.run = rundict

    return job_step


def submit_jobs_nominal(job_steps, job_scripts, workspace, adapter):
    subrecords = []
    for jstep, jscript in zip(job_steps, job_scripts):
        subrecords.append(adapter.submit(jstep, jscript, workspace))

    return subrecords

def submit_jobs_bulk(job_steps, job_scripts, workspace, adapter):
    subrecords = []
    workspaces = [workspace for jstep in job_steps]
    for srecord in adapter.bulk_submit(job_steps, job_scripts, workspaces):
        subrecords.append(srecord)

    return subrecords

def submit_jobs_bulk_async(job_steps, job_scripts, workspace, adapter, executor):
    subrecords = []
    workspaces = [workspace for jstep in job_steps]
    for srecord in adapter.bulk_submit_async(job_steps, job_scripts, workspaces, executor):
        print(f"{srecord}")
        subrecords.append(srecord)

    return subrecords

# def submit_jobs_async(job_steps, job_scripts, workspace, adapter):
#     subrecords = []
#     workspaces = [workspace for jstep in job_steps]
#     with FluxExecutor() as executor:
#         submit_futures = []
#         for jstep, jscript in zip(job_steps, job_scripts):
#             subrecords.append(adapter.submit_async(jstep
#     # for srecord in adapter.bulk_submit(job_steps, job_scripts, workspaces):
#     #     subrecords.append(srecord)

#     return subrecords


def setup_argparse():
    parser = argparse.ArgumentParser(description="program")

    # parser.add_argument('', nargs='+',
    #                     help='positional argument')

    parser.add_argument('-t', '--use-tmp', action='store_true',
                        help='Use temp workspace')

    parser.add_argument('-n', '--num-tasks',
                        type=int,
                        help='Number of tasks to submit')

    return parser


def main():
    parser = setup_argparse()

    cli_args = parser.parse_args()

    ntasks = cli_args.num_tasks

    # Setup some of the default resource info the adapter wants
    # NOTE: does `nodes=1` make sense as a default as opposed to None? implies
    # it's wanting exclusive access..
    # Min set:
    #  walltime:  set by step
    #  version: automatically determine flux adapter version
    #  flux_version: automatically determined version of flux scheduler
    #  nodes: default 1, overridden by step
    #  ntasks: set by step
    #  flux_uri: automatically determined from FLUX_URI env var if started in allocation

    # Get script adapter
    flux_adapter = FluxScriptAdapter()
    # pprint(flux_adapter)
    # pprint(dir(flux_adapter))

    # Build list of random sleep/no-op jobs
    sleep_times = [1 for n in range(ntasks)]
    walltimes = [sleep_time + 0.5 for sleep_time in sleep_times]
    job_steps = [dummy_step_builder(idx, sleep_time, walltime) for idx, (sleep_time, walltime) in enumerate(zip(sleep_times, walltimes))]
    # pprint(job_steps)

    # Setup temp workspace for the test
    if cli_args.use_tmp:
        workspace = tempfile.mkdtemp()
    else:
        workspace = Path.cwd() / '{}_{}'.format(
            f'dummy_study_{ntasks}_tasks',
            time.strftime('%Y%m%d-%H%M%S')
        )
        Path.mkdir(workspace)

    job_scripts = []
    for job_step in job_steps:
        # pprint(job_step)
        sched, script, restart = flux_adapter.write_script(workspace, job_step)
        job_scripts.append(script)
        # pprint(script)

    workspaces = [workspace for job_step in job_steps]

    with FluxExecutor() as executor:
        start_time = time.perf_counter()
        for srecord in flux_adapter.bulk_submit_async(job_steps, job_scripts, workspaces, executor):
            cur_task_dt = time.perf_counter() - start_time
            pprint(f"Time to jobid: {cur_task_dt}")
            pprint(srecord)

        tot_time = time.perf_counter() - start_time
        pprint(f"Total submit time: {tot_time} s")
        pprint(f"Jobs submission rate: {len(job_steps)/tot_time} jobs/s")
        # ADD check loop to wait till jobs finish
        
    return
    # Submit jobs
    with cProfile.Profile() as profile:
        # subrecords = submit_jobs_nominal(job_steps, job_scripts, workspace, flux_adapter)
        subrecords = submit_jobs_bulk(job_steps, job_scripts, workspace, flux_adapter)
        (
            pstats.Stats(profile)
            .strip_dirs()
            .sort_stats(pstats.SortKey.CALLS)
            .print_stats()
        )
        # pprint(subrecords)
        
    # Await the job ids

    # Cleanup: loop, polling until jobs are complete


if __name__ == "__main__":
    sys.exit(main())
