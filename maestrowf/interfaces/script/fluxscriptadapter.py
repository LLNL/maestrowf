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
from maestrowf.utils import make_safe_path

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

        # Store the interface we're using
        _version = kwargs.pop("version", FluxFactory.latest)
        self.add_batch_parameter("version", _version)
        self._interface = FluxFactory.get_interface(_version)
        # Note, should we also log parsed 'base version' used when comparing
        # the adaptor/broker versions along with the raw string we get back
        # from flux.
        self._broker_version = self._interface.get_flux_version()

        uri = kwargs.pop("uri", None)
        if not uri:             # Check if flux uri env var is set, log if so
            uri = os.environ.get("FLUX_URI", None)
            if uri:
                LOGGER.info(f"Found FLUX_URI in environment, scheduling jobs to broker uri {uri}")
            else:
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
        self._allocation_args = kwargs.get("allocation_args", {})
        LOGGER.info(f"Allocation args: {self._allocation_args}")
        self._launcher_args = kwargs.get("launcher_args", {})
        self._addl_args = kwargs.get("args", {})

        
        # Setup prefixes associated with each kind of option for routing to
        # appropriate jobspec api's
        # Additional args can pass through on launcher only, using rule of
        # verbose has '--' prefix, '=' flag/value separator and
        # brief has '-' prefix, ' ' flag/value seaprator: e.g.
        # --setattr=foo=bar, or -S foo=bar
        self._brief_arg_info = {"prefix": "-", "sep": " "}
        self._verbose_arg_info = {"prefix": "--", "sep": "="}

        # Setup known arg types
        self._known_alloc_arg_types = ["attributes", "shell_options", "conf"]
        self._allocation_args_map = {
            "setopt": "shell_options",
            "o": "shell_options",
            "setattr": "attributes",
            "S": "attributes",
            "conf": "conf",
        }

        # setup template string that all flux cli args/batch directives use for rendering
        self._flux_arg_str = "{prefix}{key}{sep}{value}"
        
        self._attr_prefixes = ['S', 'setattr']
        self._opts_prefixes = ['o', 'setopt']
        self._conf_prefixes = ['conf']  # No abbreviated form for this in flux docs

        # Add --setattr fields to batch job/broker; default to "" such
        # that 'truthiness' can exclude them from the jobspec if not provided
        queue = kwargs.pop("queue", "")
        bank = kwargs.pop("bank", "")
        available_queues = self._interface.get_broker_queues()
        # Ignore queue if specified and we detect broker only has anonymous queue
        if not available_queues and queue:
            LOGGER.info(
                "Flux Broker '%s' only has an anonymous queue: "
                "ignoring batch setting '%s'",
                uri,
                queue,
            )
            queue = ""

        self._batch_attrs = {
            "system.queue": queue,
            "system.bank": bank,
        }
        self.add_batch_parameter("queue", queue)
        self.add_batch_parameter("bank", bank)

        # Pop off the exclusive flags (NOTE: usually comes from steps, not through constructor?)
        step_exclusive = 'exclusive' in kwargs  # Track whether it was in there at all
        self._exclusive = self.get_exclusive(kwargs.pop("exclusive", False))  # Default to old < 1.1.12 behavior

        # Check for the flag in additional args and pop it off, letting step key win later
        # NOTE: only need presence of key as this mimics cli like flag behavior
        # TODO: promote this to formally supported behavior for all adapters
        exclusive_keys = ['x', 'exclusive']
        if all(ekey in self._allocation_args for ekey in exclusive_keys):
            LOGGER.warn("Repeated addition of exclusive flags 'x' and 'exclusive' in allocation_args.")

        alloc_eflags = [self._allocation_args.pop(ekey, None) for ekey in exclusive_keys]
        if alloc_eflags:
            if step_exclusive:
                LOGGER.warn("Overriding batch block allocation_args with steps exclusive setting '%s'",
                            exclusive)
            else:
                self._exclusive['allocation'] = True

        if all(ekey in self._launcher_args for ekey in exclusive_keys):
            LOGGER.warn("Repeated addition of exclusive flags 'x' and 'exclusive' in launcher_args.")

        launcher_eflags = [self._launcher_args.pop(ekey, None) for ekey in exclusive_keys]
        if launcher_eflags:
            if step_exclusive and self._exclusive['launcher']:
                LOGGER.warn("Overriding batch block launcher_args with steps exclusive setting '%s'",
                            exclusive)
            else:
                self._exclusive['launcher'] = True

        # NOTE: 
        self.add_batch_parameter("exclusive", self._exclusive['allocation'])

        # Populate formally supported flux directives in the header
        self._flux_directive = "#flux: "
        self._header = {
            "nodes": f"{self._flux_directive}" + "-N {nodes}",
            # NOTE: always use seconds to guard against upstream default behavior changes
            "walltime": f"{self._flux_directive}" + "-t {walltime}s",
            "queue": f"{self._flux_directive}" + "-q {queue}",
            "bank": f"{self._flux_directive}" + "--bank {bank}",

        }

        self._cmd_flags = {
            "ntasks": "-n",
            "nodes": "-N",
        }
        self._extension = "flux.sh"
        self.h = None

        # Addition info flags to add to the header: MAESTRO only! flux ignores
        # anything after first non-flux-directive line so this must go last
        self._info_directive = "#INFO "
        self._header_info = {
            "version": f"{self._info_directive}" + "(flux adapter version) {version}",
            "flux_version": f"{self._info_directive}" + "(flux version) {flux_version}"
        }

        if uri:
            self.add_batch_parameter("flux_uri", uri)
            self._header_info['flux_uri'] = f"{self._info_directive}" + "(flux_uri) {flux_uri}"

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

    def render_additional_args(self, args_dict):
        """
        Helper to render additional argument sets to flux cli format for
        use in constructing $(LAUNCHER) line and flux batch directives.

        :param args_dict: Dictionary of flux arg keys and name: value pairs
        """
        def arg_info_type(arg_key):
            if len(arg_key) == 1:
                return {"prefix": "-", "sep": " "}
            else:
                return {"prefix": "--", "sep": "="}

        def render_arg_value(arg_name, arg_value):
            # Handling for flag type values, e.g. -o fastload
            if arg_value:
                return f"{arg_name}={arg_value}"
            else:
                return f"{arg_name}"

        for arg_key, arg_value in args_dict.items():
            arg_info = arg_info_type(arg_key)

            for av_name, av_value in arg_value.items():
                value_str = render_arg_value(av_name, av_value)
                yield "{prefix}{key}{sep}{value}".format(
                    prefix=arg_info['prefix'],
                    key=arg_key,
                    sep=arg_info['sep'],
                    value=value_str
                )

    def pack_addtl_batch_args(self):
        """
        Normalize the allocation args and pack up into the interface specific
        groups that have assocated jobspec methods, e.g. conf, setattr, setopt.

        :return: dictionary of allocation arg groups to attach to jobspecs
        """
        addtl_batch_args = {
            arg_type: {}
            for arg_type in self._interface.addtl_alloc_arg_types
        }
        for arg_key, arg_values in self._allocation_args.items():
            # TODO: move this into a validation function for pre launch
            #       batch args validation
            arg_type = self._interface.addtl_alloc_arg_type_map(arg_key)
            if arg_type is None:
                # NO WARNINGS HERE: args in 'misc' type handled elsewhere
                # TODO: add better mechanism for tracking whicn args
                #       actually get used; dicts can't do this..
                continue

            new_arg_values = arg_values
            # Match default of flag types in flux cli.
            # see https://github.com/flux-framework/flux-core/blob/a3860d4dea5b5a17c473cff4385276e882275252/src/bindings/python/flux/cli/base.py#L734
            # NOTE: only doing this in alloc; let LAUNCHER cli pass through
            #       to flux cli (None values are omittied, e.g.
            #       {o: fastload: None} renders to -o fastload
            #       Python api doesn't appear to have default value handling?
            for key, value in new_arg_values.items():
                if value is None:
                    value = 1

            addtl_batch_args[arg_type].update(new_arg_values)

        return addtl_batch_args

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

        # Handle exclusive flag
        step_exclusive_given = "exclusive" in step.run
        step_exclusive = self._exclusive
        if step_exclusive_given:
            # Override the default with this step's setting
            step_exclusive.update(self.get_exclusive(step.run.get("exclusive", False)))

        if step_exclusive['allocation']:
            modified_header.append(f"{self._flux_directive}" + "--exclusive")

        # Process any optional allocation args
        for rendered_arg in self._interface.render_additional_args(self._allocation_args):
            if rendered_arg:
                # Silent pass through for old versions which don't implement any
                # interface for batch/allocation args
                modified_header.append(f"{self._flux_directive}" + rendered_arg)

        # Process INFO lines at the end: flux stops parsing directives after any
        # lines starting tag+prefix (e.g. "#flux:" ) that doesn't match the flux directives
        for key, value in self._header_info.items():
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
        
        # Handle the exclusive flags, updating batch block settings (default)
        # with what's set in the step
        step_exclusive_given = "exclusive" in kwargs
        step_exclusive = self._exclusive
        if step_exclusive_given:
            # Override the default with this step's setting
            step_exclusive.update(self.get_exclusive(kwargs.get("exclusive", False)))

        # TODO: fix this temp hack when standardizing the exclusive key handling
        kwargs['exclusive'] = step_exclusive['launcher']
        
        return self._interface.parallelize(
            procs, nodes=ntasks, addtl_args=self._addl_args,
            launcher_args=self._launcher_args, **kwargs)

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

        force_broker = step.run.get("nested", True)
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

        # Handle the exclusive flags, updating batch block settings (default)
        # with what's set in the step
        step_exclusive_given = "exclusive" in step.run
        step_exclusive = self._exclusive
        if step_exclusive_given:
            # Override the default with this step's setting
            step_exclusive.update(self.get_exclusive(step.run.get("exclusive", False)))

        # Unpack waitable flag and pass it along if there: only pass it along if
        # it's in the step maybe, leaving each adapter to retain their defaults?
        waitable = step.run.get("waitable", False)

        jobid, retcode, submit_status = \
            self._interface.submit(
                nodes, processors, cores_per_task, path, cwd, walltime, ngpus,
                job_name=step.name, force_broker=force_broker, urgency=urgency,
                waitable=waitable,
                addtl_batch_args=self.pack_addtl_batch_args(),
                exclusive=step_exclusive['allocation']
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
        script_path = make_safe_path(ws_path, fname)
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
