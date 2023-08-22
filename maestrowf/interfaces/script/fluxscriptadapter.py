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

"""Flux Scheduler interface implementation."""
import logging
from math import ceil
import os
import re

from maestrowf.abstracts.interfaces import SchedulerScriptAdapter
from maestrowf.abstracts.enums import JobStatusCode, CancelCode
from maestrowf.interfaces.script import CancellationRecord, SubmissionRecord, \
    FluxFactory

LOGGER = logging.getLogger(__name__)
status_re = re.compile(r"Job \d+ status: (.*)$")
# env_filter = re.compile(r"^(SSH_|LSF)")
env_filter = re.compile(r"^SSH_")


class FluxScriptAdapter(SchedulerScriptAdapter):
    """Interface class for the flux scheduler (on Spectrum MPI)."""

    key = "flux"

    def __init__(self, **kwargs):
        """
        Initialize an instance of the FluxScriptAdapter.

        The FluxScriptAdapter is this package interface to the Flux
        scheduler. This adapter constructs Flux scripts for a StudyStep based
        on user set defaults and local settings present in each step.

        The expected keyword arguments that are expected when the Flux adapter
        is instantiated are as follows:
        * host: The cluster to execute scripts on.
        * bank: The account to charge computing time to.
        * queue: Scheduler queue scripts should be submitted to.
        * nodes: The number of compute nodes to be reserved for computing.

        :param **kwargs: A dictionary with default settings for the adapter.
        """
        super(FluxScriptAdapter, self).__init__(**kwargs)

        
        uri = kwargs.pop("uri", None)
        if not uri:             # Check if flux uri env var is set, log if so
            uri = os.environ.get("FLUX_URI", None)
            if uri:
                LOGGER.info(f"Found FLUX_URI in environment, scheduling jobs to broker uri {uri}")
            LOGGER.info(f"No FLUX_URI; scheduling standalone batch job to root instance")
        else:
            LOGGER.info(f"Using FLUX_URI found in study specification: {uri}")
        # if not uri:
        #     raise ValueError(
        #         "Flux URI must be specified in batch or stored in the "
        #         "environment under 'FLUX_URI'")

        # NOTE: Host doesn"t seem to matter for FLUX. sbatch assumes that the
        # current host is where submission occurs.
        self.add_batch_parameter("nodes", kwargs.pop("nodes", "1"))
        self._addl_args = kwargs.get("args", {})

        # Header is only for informational purposes.
        self._header = {
            "nodes": "#INFO (nodes) {nodes}",
            "walltime": "#INFO (walltime) {walltime}",
            "version": "#INFO (flux adapter version) {version}",
            "flux_version": "#INFO (flux version) {flux_version}",
        }

        self._cmd_flags = {
            "ntasks": "-n",
            "nodes": "-N",
        }
        self._extension = "flux.sh"
        self.h = None

        if uri:
            self.add_batch_parameter("flux_uri", uri)
            self._header['flux_uri'] = "#INFO (flux_uri) {flux_uri}"

        # Store the interface we're using
        _version = kwargs.pop("version", FluxFactory.latest)
        self.add_batch_parameter("version", _version)
        self._interface = FluxFactory.get_interface(_version)
        # Note, should we also log parsed 'base version' used when comparing
        # the adaptor/broker versions along with the raw string we get back
        # from flux.
        self._broker_version = self._interface.get_flux_version()

    @property
    def extension(self):
        return self._extension

    def _convert_walltime_to_seconds(self, walltime):
        if isinstance(walltime, int) or isinstance(walltime, float):
            LOGGER.debug("Encountered numeric walltime = %s", str(walltime))
            return int(float(walltime) * 60.0)
        elif isinstance(walltime, str) and walltime.isnumeric():
            LOGGER.debug("Encountered numeric walltime = %s", str(walltime))
            return int(float(walltime) * 60.0)
        elif ":" in walltime:
            # Convert walltime to seconds.
            LOGGER.debug("Converting %s to seconds...", walltime)
            seconds = 0.0
            for i, value in enumerate(walltime.split(":")[::-1]):
                seconds += float(value) * (60.0 ** i)
            return seconds
        elif not walltime or (isinstance(walltime, str) and walltime == "inf"):
            return 0
        else:
            msg = \
                f"Walltime value '{walltime}' is not an integer or colon-" \
                f"separated string."
            LOGGER.error(msg)
            raise ValueError(msg)

    def get_header(self, step):
        """
        Generate the header present at the top of Flux execution scripts.

        :param step: A StudyStep instance.
        :returns: A string of the header based on internal batch parameters and
                  the parameter step.
        """
        run = dict(step.run)
        batch_header = dict(self._batch)
        walltime = step.run.get("walltime", None)
        batch_header["walltime"] = \
            str(self._convert_walltime_to_seconds(walltime))

        if run["nodes"]:
            batch_header["nodes"] = run.pop("nodes")
        batch_header["job-name"] = step.name.replace(" ", "_")
        batch_header["comment"] = step.description.replace("\n", " ")
        batch_header["flux_version"] = self._broker_version

        modified_header = ["#!{}".format(self._exec)]
        for key, value in self._header.items():
            if key not in batch_header:
                continue
            modified_header.append(value.format(**batch_header))

        return "\n".join(modified_header)

    def get_parallelize_command(self, procs, nodes=None, **kwargs):
        """
        Generate the FLUX parallelization segement of the command line.

        :param procs: Number of processors to allocate to the parallel call.
        :param nodes: Number of nodes to allocate to the parallel call
                      (default = 1).
        :returns: A string of the parallelize command configured using nodes
                  and procs.
        """
        ntasks = nodes if nodes else self._batch.get("nodes", 1)
        return self._interface.parallelize(
            procs, nodes=ntasks, addtl_args=self._addl_args, **kwargs)

    def submit(self, step, path, cwd, job_map=None, env=None):
        """
        Submit a script to the Flux scheduler.

        :param step: The StudyStep instance this submission is based on.
        :param path: Local path to the script to be executed.
        :param cwd: Path to the current working directory.
        :param job_map: A dictionary mapping step names to their job
                        identifiers.
        :param env: A dict containing a modified environment for execution.
        :returns: The return status of the submission command and job
                  identiifer.
        """
        nodes = step.run.get("nodes", 1)
        processors = step.run.get("procs", 0)

        if not isinstance(nodes, int):
            if not nodes:
                nodes = 1
            else:
                nodes = int(nodes)

        if not isinstance(processors, int):
            if not processors:
                processors = 1
            else:
                processors = int(processors)
                
        force_broker = step.run.get("nested", False)
        walltime = \
            self._convert_walltime_to_seconds(step.run.get("walltime", 0))
        urgency = step.run.get("priority", "medium")
        urgency = self.get_priority(urgency)

        # Compute cores per task
        cores_per_task = step.run.get("cores per task", None)
        if isinstance(cores_per_task, str):
            try:
                cores_per_task = int(cores_per_task)
            except:
                cores_per_task = 1
        if not cores_per_task:
            cores_per_task = 1 # max((1, ceil(processors / nodes)))
            LOGGER.warn(
                "'cores per task' set to a non-value. Populating with a "
                "sensible default. (cores per task = %d", cores_per_task)

        try:
            # Calculate ngpus
            ngpus = step.run.get("gpus", "0")
            ngpus = int(ngpus) if ngpus else 0
        except ValueError as val_error:
            msg = f"Specified gpus '{ngpus}' is not a decimal value."
            LOGGER.error(msg)
            raise val_error

        # Calculate nprocs
        ncores = cores_per_task * nodes
        # Raise an exception if ncores is 0
        if ncores <= 0:
            msg = "Invalid number of cores specified. " \
                  "Aborting. (ncores = {})".format(ncores)
            LOGGER.error(msg)
            raise ValueError(msg)

        # Unpack waitable flag and pass it along if there: only pass it along if
        # it's in the step maybe, leaving each adapter to retain their defaults?
        waitable = step.run.get("waitable", False)
        jobid, retcode, submit_status = \
            self._interface.submit(
                nodes, processors, cores_per_task, path, cwd, walltime, ngpus,
                job_name=step.name, force_broker=force_broker, urgency=urgency,
                waitable=waitable
            )

        return SubmissionRecord(submit_status, retcode, jobid)

    def check_jobs(self, joblist):
        """
        For the given job list, query execution status.

        This method uses the scontrol show job <jobid> command and does a
        regex search for job information.

        :param joblist: A list of job identifiers to be queried.
        :returns: The return code of the status query, and a dictionary of job
                  identifiers to their status.
        """
        LOGGER.debug("Joblist type -- %s", type(joblist))
        LOGGER.debug("Joblist contents -- %s", joblist)
        if not joblist:
            LOGGER.debug("Empty job list specified.")
            return JobStatusCode.OK, {}
        if not isinstance(joblist, list):
            LOGGER.debug("Specified parameter is not a list.")
            if isinstance(joblist, int):
                LOGGER.debug("Integer found.")
                joblist = [joblist]
            else:
                LOGGER.debug("Unknown type. Returning an error.")
                return JobStatusCode.ERROR, {}

        try:
            chk_status, status = self._interface.get_statuses(joblist)
        except Exception as excpt:
            LOGGER.error(str(excpt))
            status = {}
            chk_status = JobStatusCode.ERROR

        return chk_status, status

    def cancel_jobs(self, joblist):
        """
        For the given job list, cancel each job.

        :param joblist: A list of job identifiers to be cancelled.
        :returns: The return code to indicate if jobs were cancelled.
        """
        # If we don"t have any jobs to check, just return status OK.
        if not joblist:
            return CancelCode.OK

        c_status, r_code = self._interface.cancel(joblist)
        return CancellationRecord(c_status, r_code)

    def _state(self, flux_state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param flux_state: String representation of scheduler job status.
        :returns: A Study.State enum corresponding to parameter job_state.
        """
        raise NotImplementedError(
            "FluxScriptAdapter no longer uses the _state mapping.")

    def _write_script(self, ws_path, step):
        """
        Write a Flux script to the workspace of a workflow step.

        The job_map optional parameter is a map of workflow step names to job
        identifiers. This parameter so far is only planned to be used when a
        study is configured to be launched in one go (more or less a script
        chain using a scheduler dependency setting). The functionality of
        the parameter may change depending on both future intended use.

        :param ws_path: Path to the workspace directory of the step.
        :param step: An instance of a StudyStep.
        :returns: Boolean value (True if to be scheduled), the path to the
                  written script for run["cmd"], and the path to the script
                  written for run["restart"] (if it exists).
        """
        to_be_scheduled, cmd, restart = self.get_scheduler_command(step)

        fname = "{}.{}".format(step.name, self._extension)
        script_path = os.path.join(ws_path, fname)
        with open(script_path, "w") as script:
            script.write(self.get_header(step))
            cmd = "\n\n{}\n".format(cmd)
            script.write(cmd)

        if restart:
            rname = "{}.restart.{}".format(step.name, self._extension)
            restart_path = os.path.join(ws_path, rname)

            with open(restart_path, "w") as script:
                if to_be_scheduled:
                    script.write(self.get_header(step))
                else:
                    script.write(self._exec)

                cmd = "\n\n{}\n".format(restart)
                script.write(cmd)
        else:
            restart_path = None

        return to_be_scheduled, script_path, restart_path

    def get_priority(self, priority):
        return self._interface.get_flux_urgency(priority)
