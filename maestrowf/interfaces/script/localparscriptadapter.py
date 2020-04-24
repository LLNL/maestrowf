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

"""Local interface implementation."""
import logging
import os
import psutil
import signal

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures._base import PENDING as future_PENDING

from functools import partial as func_partial
from threading import Thread, RLock

from maestrowf.abstracts.enums import JobStatusCode, SubmissionCode, \
    CancelCode, State
from maestrowf.interfaces.script import CancellationRecord, SubmissionRecord
from maestrowf.abstracts.interfaces import SchedulerScriptAdapter
from maestrowf.abstracts import Singleton
from maestrowf.utils import start_process


LOGGER = logging.getLogger(__name__)


class LocalParallelScriptAdapter(SchedulerScriptAdapter):
    """A ScriptAdapter class for interfacing for parallel local execution."""

    key = "local_parallel"

    executor = None
    running_steps = {}          # needs to be singleton, threadsafe
    tasks_lock = RLock()
    total_procs = 1
    avail_procs = 1

    def __init__(self, **kwargs):
        """
        Initialize an instance of the LocalParallelScriptAdapter.

        The LocalParallelScriptAdapter is the adapter that is used for workflows that
        will execute on the user's machine. This adapter constructs shell scripts for
        a StudyStep based on user set defaults and local settings present in each step.

        These scripts are submitted to a local scheduler for asynchronous execution
        and monitoring.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        LOGGER.debug("kwargs\n--------------------------\n%s", kwargs)
        super(LocalParallelScriptAdapter, self).__init__(**kwargs)

        # Register keys
        self.add_batch_parameter("proc_count", int(kwargs.pop("proc_count", "1")))

        self._header = {
            "procs": "# procs = {procs}",
        }

        # Maybe need better types here for populating the queues?
        self.START = 0
        self.CANCEL = 1
        self.DONE = 2
        
        self.total_procs = int(kwargs.pop("proc_count", "1"))
        self.avail_procs = int(kwargs.pop("avail_procs", "1"))
        self.executor = ThreadPoolExecutor(max_workers=self.total_procs)

    def __getstate__(self):
        """Helper for excluding threadpool from pickling"""
        state = self.__dict__.copy()
        del state["executor"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Add baz back since it doesn't exist in the pickle
        self.executor = ThreadPoolExecutor(max_workers=self.total_procs)

    def _update_running_steps(self, add_tasks=None, rm_tasks=None):
        """Thread safe addition/removal of tasks from running_steps dict"""
        if not add_tasks:
            add_tasks = []

        if not rm_tasks:
            rm_tasks = []

        with self.tasks_lock:
            for task_id in rm_tasks:
                if task_id in self.running_steps:
                    self.avail_procs += self.running_steps[task_id][1]  # give back resources

                    LOGGER.debug("Removing task {} from running_steps".format(
                        self.running_steps.pop(task_id)))
                else:
                    LOGGER.error("Tried removing task {} from running_steps, "
                                 "but it was not found.".format(task_id))

            for task in add_tasks:
                for task_id in task:
                    if task_id in self.running_steps:
                        LOGGER.error("Tried adding already tracked task {} "
                                     "to running_steps.".format(task_id))
                    else:
                        LOGGER.debug("Adding task {} to running_steps".format(task_id))
                        self.running_steps[task_id] = task[task_id]

        # Want any status codes returned here if errors triggered?

    def get_header(self, step):
        """
        Generate the header present at the top of execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
            the parameter step.
        """
        return ""

    def get_parallelize_command(self, procs, nodes, **kwargs):
        """
        Generate the parallelization segement of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
            (default = 1).
        :returns: A string of the parallelize command configured using nodes
            and procs.
        :NOTE: this is currently a dummy method -> rework to add user specified replacements later
        """
        return ""

    def _state(self, fut):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param fut: Future instance representing a task
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        # NOTE: should all of this replace what's in check_jobs -> what about error code there?
        if fut.running():
            return State.RUNNING
        elif fut.done():
            if fut in self.running_steps:
                return State.FINISHING
            else:
                return State.FINISHED
        elif fut.cancelled():
            return State.CANCELLED
        elif fut._state == future_PENDING:
            return State.PENDING
        else:
            return State.UNKNOWN

    def _write_script(self, ws_path, step):
        """
        Write a shell script to the workspace of a workflow step.

        The job_map optional parameter is a map of workflow step names to job
        identifiers. This parameter so far is only planned to be used when a
        study is configured to be launched in one go (more or less a script
        chain using a scheduler's dependency setting). The functionality of
        the parameter may change depending on both future intended use.

        :param ws_path: Path to the workspace directory of the step.
        :param step: An instance of a StudyStep.
        :returns: False (will not be scheduled), the path to the
            written script for run["cmd"], and the path to the script written
            for run["restart"] (if it exists).
        """
        # THIS IS A HACK FOR NOW: make better use of get_scheduler_command later
        cmd = step.run["cmd"]
        restart = step.run["restart"]
        to_be_scheduled, _, _ = self.get_scheduler_command(step)

        fname = "{}.sh".format(step.name)
        script_path = os.path.join(ws_path, fname)
        with open(script_path, "w") as script:
            script.write("#!{0}\n\n{1}\n".format(self._exec, cmd))

        if restart:
            rname = "{}.restart.sh".format(step.name)
            restart_path = os.path.join(ws_path, rname)

            with open(restart_path, "w") as script:
                script.write("#!{0}\n\n{1}\n".format(self._exec, restart))
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path

    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        This method uses the scontrol show job <jobid> command and does a
        regex search for job information.

        :param joblist: A list of job identifiers to be queried.
        :returns: The return code of the status query, and a dictionary of job
            identifiers to their status.
        """

        status = {}
        status_code = JobStatusCode.OK
        
        for fut in joblist:
            LOGGER.debug("Looking for job with Future %s", fut)

            # Future states: running, done, cancelled
            if fut.done():
                # Check result/process retcode: subprocess errors caught here
                if fut in self.running_steps:
                    # NOTE: does the avail_procs in update_running_steps always catch ending or
                    # is there some other check needed here?
                    result=fut.result()  # this the right place to catch this?
                    LOGGER.debug("Fut {} has result: {}".format(fut, result))
                    status[fut] = State.FINISHING

                else:
                    status[fut] = State.FINISHED

            elif fut.running():
                status[fut] = State.RUNNING

            elif fut.cancelled():
                # What about cancelled pid's? that would show up under fut.done()...
                status[fut] = State.CANCELLED

            elif fut._state == future_PENDING:
                LOGGER.debug("Fut {} is pending".format(fut))
                status[fut] = State.PENDING

            else:
                print("Fut {} with unknown state".format(fut))
                if fut in self.running_steps:
                    LOGGER.debug("Fut {} is running?".format(fut))
                    LOGGER.debug("Fut {} state: running {}, done {}, cancelled {}".format(
                        fut, fut.done(), fut.running(), fut.cancelled()))
                status[fut] = State.UNKNOWN  # this ever reached, and if so how
                status_code = JobStatusCode.ERROR

        return status_code, status

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
        """
        if not joblist:
            return CancellationRecord(CancelCode.OK, 0)

        retcode = 0

        for fut in joblist:
            if fut in self.running_steps:
                if fut.done():  # cleanup
                    # Really need _submit to return submission record vs retcode/err?                    
                    result = fut.get_result()
                else:
                    # Interrupt running subprocesses
                    try:
                        process, procs = self.running_steps[fut]
                        self._kill(process.pid) #process.kill()    # better way to kill it?
                        fut.result()  # wait on future to exit
                    except KeyError:
                        LOGGER.error("Error, future {}, no longer in running step list".format(fut))
                        retcode += 1

                    except:     # TODO: catch exceptions from kill(), get_result()
                        LOGGER.exception("Error, unexpected behavior trying to cancel future {}, "
                                     "and subprocess with id {}".format(fut, process.pid))
                        retcode += 1
                        
            if not fut.done() and not fut.running():
                # This shouldn't be hit since execution graph only submits if resources available
                LOGGER.error("Error, encounterd future {} in unexpected state".format(fut))
                retcode += 1

        if retcode == 0:
            _record = CancellationRecord(CancelCode.OK, retcode)
        else:
            LOGGER.error("Error code '%s' seen. Unexpected behavior "
                         "encountered.")  # NOTE: what does logger.error inject in %s?
            _record = CancellationRecord(CancelCode.ERROR, retcode)

        return _record

    @staticmethod
    def _kill(subprocess_pid, sig=signal.SIGTERM, include_parent=True):
        """Kill a process tree (including grandchildren) with signal
        "sig" and return a (gone, still_alive) tuple.
        "on_terminate", if specified, is a callabck function which is
        called as soon as a child terminates.
        
        NOTE: borrowed from recipe in psutil docs
        """
        assert subprocess_pid != os.getpid(), "won't kill myself"
        parent = psutil.Process(subprocess_pid)
        children = parent.children(recursive=True)
        if include_parent:
            children.append(parent)

        for p in children:
            p.send_signal(sig)
            LOGGER.debug("Killing process {}".format(p.name()))

        gone, alive = psutil.wait_procs(children, timeout=5,
                                        callback=None)

        LOGGER.debug("  Gone, alive = {}, {}".format(gone, alive))
        # return (gone, alive)

    def _submit(self, p, step, path, cwd, job_map=None, env=None):
        """
        Execute the step locally.

        If cwd is specified, the submit method will operate outside of the path
        specified by the 'cwd' parameter.
        If env is specified, the submit method will set the environment
        variables for submission to the specified values. The 'env' parameter
        should be a dictionary of environment variables.

        :param p: Subprocess object
        :param step: An instance of a StudyStep.
        :param path: Path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A map of workflow step names to their job identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return code of the submission command and job identiifer.
        """
        LOGGER.debug("cwd = %s", cwd)
        LOGGER.debug("Script to execute: %s", path)

        pid = p.pid
        output, err = p.communicate()
        retcode = p.wait()

        o_path = os.path.join(cwd, "{}.out".format(step.name))
        e_path = os.path.join(cwd, "{}.err".format(step.name))

        with open(o_path, "w") as out:
            out.write(output)

        with open(e_path, "w") as out:
            out.write(err)

        if retcode == 0:
            LOGGER.info("Execution returned status OK.")
            return SubmissionRecord(SubmissionCode.OK, retcode, pid)
        else:
            LOGGER.warning("Execution returned an error: %s", str(err))
            _record = SubmissionRecord(SubmissionCode.ERROR, retcode, pid)
            _record.add_info("stderr", str(err))
            return _record

    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Execute the step locally.

        If cwd is specified, the submit method will operate outside of the path
        specified by the 'cwd' parameter.
        If env is specified, the submit method will set the environment
        variables for submission to the specified values. The 'env' parameter
        should be a dictionary of environment variables.

        :param step: An instance of a StudyStep.
        :param path: Path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A map of workflow step names to their job identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return code of the submission command and job identiifer.
        """
        try:
            p = start_process(path, shell=False, cwd=cwd, env=env)
            fut = self.executor.submit(self._submit, p, step, path, cwd, job_map=None, env=None)
            try:
                step_procs = step.run.get("procs")
                if not step_procs:
                    step_procs = 1
                else:
                    step_procs = int(step_procs)
            except ValueError:
                step_procs = 1
                LOGGER.error("Starting step {} with no 'procs' attribute with 1 processor.".format(_record.step.name))

            self.avail_procs -= step_procs

        except:                 # add some relevant exceptions here..
            LOGGER.warning("Execution returned an error")

            _record = SubmissionRecord(SubmissionCode.ERROR, -1)
            self.avail_procs += step_procs
            return _record

            #     self.avail_procs -= step._procs
            # except:

        # Update running task list.  Thread safe list be better?

        self._update_running_steps(add_tasks=[{fut:(p, step_procs)}])
        # fut.add_done_callback(func_partial(self._task_callback, fut, rm_func=self._update_running_steps))
        fut.add_done_callback(self.wrap_callback(self._update_running_steps))

        LOGGER.info("Execution returned status OK.")
        return SubmissionRecord(SubmissionCode.OK, 0, fut)

    @staticmethod
    def wrap_callback(rm_func):
        def task_callback(fut):
            #fut.result()
            rm_func(add_tasks=None, rm_tasks=[fut])

        return task_callback

    @staticmethod
    def _task_callback(fut, rm_func):
        fut.get_result()
        rm_func(add_tasks=None, rm_tasks=[fut])
