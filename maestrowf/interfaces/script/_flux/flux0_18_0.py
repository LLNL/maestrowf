import errno
import logging
from math import ceil
import os

from maestrowf.abstracts.enums import CancelCode, JobStatusCode, State, \
    SubmissionCode
from maestrowf.abstracts.interfaces.flux import FluxInterface

LOGGER = logging.getLogger(__name__)

try:
    from flux import constants as flux_constants
    from flux import job as flux_job
except ImportError:
    LOGGER.info("Failed to import Flux. Continuing.")


class FluxInterface_0190(FluxInterface):
    # This utility class is for Flux 0.19.0
    key = "0.19.0"

    _FIELDATTRS = {
        "id": (),
        "userid": ("userid",),
        "username": ("userid",),
        "priority": ("priority",),
        "state": ("state",),
        "state_single": ("state",),
        "name": ("name",),
        "ntasks": ("ntasks",),
        "nnodes": ("nnodes",),
        "ranks": ("ranks",),
        "success": ("success",),
        "exception.occurred": ("exception_occurred",),
        "exception.severity": ("exception_severity",),
        "exception.type": ("exception_type",),
        "exception.note": ("exception_note",),
        "result": ("result",),
        "result_abbrev": ("result",),
        "t_submit": ("t_submit",),
        "t_depend": ("t_depend",),
        "t_sched": ("t_sched",),
        "t_run": ("t_run",),
        "t_cleanup": ("t_cleanup",),
        "t_inactive": ("t_inactive",),
        "runtime": ("t_run", "t_cleanup"),
        "runtime_fsd": ("t_run", "t_cleanup"),
        "runtime_hms": ("t_run", "t_cleanup"),
        "status": ("state", "result"),
        "status_abbrev": ("state", "result"),
    }

    attrs = set(
        _FIELDATTRS["userid"] + _FIELDATTRS["status"]
    )

    flux_handle = None

    @classmethod
    def submit(
        cls, nodes, procs, cores_per_task, path, cwd, walltime,
        ngpus=0, job_name=None, force_broker=False, waitable=True
    ):
        cls.connect_to_flux()

        # NOTE: This previously placed everything under a broker. However,
        # if there's a job that schedules items to Flux, it will schedule all
        # new jobs to the sub-broker. Sometimes this is desired, but it's
        # incorrect to make that the general case. If we are asking for a
        # single node, don't use a broker -- but introduce a flag that can
        # force a single node to run in a broker.

        if force_broker or nodes > 1:
            LOGGER.debug(
                "Launch under Flux sub-broker. [force_broker=%s, nodes=%d]",
                force_broker, nodes
            )
            ngpus_per_slot = int(ceil(ngpus / nodes))
            jobspec = flux_job.JobspecV1.from_nest_command(
                [path], num_nodes=nodes, cores_per_slot=cores_per_task,
                num_slots=nodes, gpus_per_slot=ngpus_per_slot)
        else:
            LOGGER.debug(
                "Launch under root Flux broker. [force_broker=%s, nodes=%d]",
                force_broker, nodes
            )
            jobspec = flux_job.JobspecV1.from_command(
                [path], num_tasks=procs, num_nodes=nodes,
                cores_per_task=cores_per_task, gpus_per_task=ngpus)

        LOGGER.debug("Handle address -- %s", hex(id(cls.flux_handle)))
        if job_name:
            jobspec.setattr("system.job.name", job_name)
        jobspec.cwd = cwd
        jobspec.environment = dict(os.environ)

        if walltime > 0:
            jobspec.duration = walltime

        jobspec.stdout = f"{job_name}.{{{{id}}}}.out"
        jobspec.stderr = f"{job_name}.{{{{id}}}}.err"

        try:
            # Submit our job spec.
            jobid = \
                flux_job.submit(cls.flux_handle, jobspec, waitable=waitable)
            submit_status = SubmissionCode.OK
            retcode = 0

            LOGGER.info("Submission returned status OK. -- "
                        "Assigned identifier (%s)", jobid)
        except Exception as exception:
            LOGGER.error(
                "Submission failed -- Message (%s).", exception)
            jobid = -1
            retcode = -1
            submit_status = SubmissionCode.ERROR

        return jobid, retcode, submit_status

    @classmethod
    def parallelize(cls, procs, nodes=None, **kwargs):
        args = ["flux", "mini", "run", "-n", str(procs)]

        # if we've specified nodes, add that to wreckrun
        ntasks = nodes if nodes else 1
        args.append("-N")
        args.append(str(ntasks))

        if "cores per task" in kwargs:
            args.append("-c")
            args.append(str(kwargs["cores per task"]))

        # flux has additional arguments that can be passed via the '-o' flag.
        addtl = []
        addtl_args = kwargs.get("addtl_args", {})
        for key, value in addtl_args.items():
            addtl.append(f"{key}={value}")

        if addtl:
            args.append("-o")
            args.append(",".join(addtl))

        return " ".join(args)

    @staticmethod
    def status_callback(future, args):
        jobid, cb_args = args
        try:
            job = future.get_job()
            e_stat = "S"
        except EnvironmentError as err:
            job = {'id': jobid}
            if err.errno == errno.ENOENT:
                LOGGER.error("Flux Job identifier '%s' not found.", jobid)
                e_stat = "NF"
            else:
                LOGGER.error("Flux RPC: {}", err.strerror)
                e_stat = "UNK"

        cb_args["jobs"].append((e_stat, job))
        cb_args["count"] += 1
        if cb_args["count"] == cb_args["total"]:
            cb_args["handle"].reactor_stop(future.get_reactor())

    @classmethod
    def get_statuses(cls, joblist):
        # We need to import flux here, as it may not be installed on
        # all systems.
        cls.connect_to_flux()

        LOGGER.debug(
            "Handle address -- %s", hex(id(cls.flux_handle)))

        cb_args = {
            "jobs":   [],
            "handle": cls.flux_handle,
            "count":  0,
            "total": len(joblist),
        }

        for jobid in joblist:
            rpc_handle = flux_job.job_list_id(
                cls.flux_handle, int(jobid), list(cls.attrs))
            rpc_handle.then(cls.status_callback, arg=(int(jobid), cb_args))
        ret = cls.flux_handle.reactor_run(rpc_handle.get_reactor(), 0)

        LOGGER.debug("Reactor return code: %d", ret)
        if ret == 1:
            chk_status = JobStatusCode.OK
        else:
            chk_status = JobStatusCode.ERROR

        statuses = {}
        for job_entry in cb_args["jobs"]:
            if job_entry[0] == "NF":
                statuses[job_entry[1]["id"]] = State.NOTFOUND
            elif job_entry[0] == "UNK":
                statuses[job_entry[1]["id"]] = State.UNKNOWN
            else:
                LOGGER.debug(
                    "Job checked with status '%s'\nEntry: %s",
                    job_entry[0], job_entry[1])
                statuses[job_entry[1]["id"]] = \
                    cls.statustostr(job_entry[1], True)
        return chk_status, statuses

    @classmethod
    def resulttostr(cls, resultid, singlechar=False):
        # if result not returned, just return empty string back
        inner = __import__("flux.core.inner", fromlist=["raw"])
        if resultid == "":
            return ""

        LOGGER.debug(
            "Calling 'inner.raw.flux_job_resulttostr' with (%s, %s)",
            resultid, singlechar)
        ret = inner.raw.flux_job_resulttostr(resultid, singlechar)
        return ret.decode("utf-8")

    @classmethod
    def statustostr(cls, job_entry, abbrev=True):
        stateid = job_entry["state"]
        LOGGER.debug(
            "JOBID [%d] -- Encountered (%s)", job_entry["id"], stateid)

        if stateid & flux_constants.FLUX_JOB_PENDING:
            LOGGER.debug("Marking as PENDING.")
            statusstr = "PD" if abbrev else "PENDING"
        elif stateid & flux_constants.FLUX_JOB_RUNNING:
            LOGGER.debug("Marking as RUNNING.")
            statusstr = "R" if abbrev else "RUNNING"
        else:
            LOGGER.debug(
                "Found Flux INACTIVE state. Calling resulttostr (result=%s).",
                job_entry["result"])
            statusstr = cls.resulttostr(job_entry["result"], abbrev)
        return cls.state(statusstr)

    @classmethod
    def cancel(cls, joblist):
        """
        Cancel a job using Flux 0.17.0 cancellation API.

        :param joblist: A list of job identifiers to cancel.
        :return: CancelCode enumeration that reflects result of cancellation.
        "return: A cancel return code indicating how cancellation call exited.
        """
        # We need to import flux here, as it may not be installed on
        # all systems.
        cls.connect_to_flux()

        LOGGER.debug(
            "Handle address -- %s", hex(id(cls.flux_handle)))
        LOGGER.debug(
            "Attempting to cancel jobs.\nJoblist:\n%s",
            "\n".join(str(j) for j in joblist)
        )

        cancel_code = CancelCode.OK
        cancel_rcode = 0
        for entry in joblist:
            try:
                LOGGER.debug("Cancelling Job %s...", entry)
                entry.cancel(cls.flux_handle, int(entry))
            except Exception as exception:
                LOGGER.error(str(exception))
                cancel_code = CancelCode.ERROR
                cancel_rcode = 1

        return cancel_code, cancel_rcode

    @staticmethod
    def state(state):
        if state == "CD":
            return State.FINISHED
        elif state == "F":
            return State.FAILED
        elif state == "R":
            return State.RUNNING
        elif state == "PD":
            return State.PENDING
        elif state == "C":
            return State.CANCELLED
        elif state == "TO":
            return State.TIMEDOUT
        else:
            return State.UNKNOWN
