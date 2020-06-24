import errno
import logging

from maestrowf.abstracts.enums import JobStatusCode, State
from maestrowf.abstracts.interfaces.flux import FluxInterface

LOGGER = logging.getLogger(__name__)


class FluxInterface_0170(FluxInterface):
    # This utility class is for Flux 0.17.0
    key = "0.17.0"

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

    @classmethod
    def parallelize(cls, procs, nodes=None, **kwargs):
        args = ["flux", "mini", "run", "-n", str(procs)]

        # if we've specified nodes, add that to wreckrun
        ntasks = nodes if nodes else 1
        args.append("-N")
        args.append(str(ntasks))

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
    def get_statuses(cls, handle, joblist):
        # We need to import flux here, as it may not be installed on
        # all systems.
        flux = __import__("flux", fromlist=["job"])

        cb_args = {
            "jobs":   [],
            "handle": handle,
            "count":  0,
            "total": len(joblist),
        }

        for jobid in joblist:
            rpc_handle = \
                flux.job.job_list_id(handle, int(jobid), list(cls.attrs))
            rpc_handle.then(cls.status_callback, arg=(int(jobid), cb_args))
        ret = handle.reactor_run(rpc_handle.get_reactor(), 0)

        if ret == 2:
            chk_status = JobStatusCode.OK
        else:
            chk_status = JobStatusCode.ERROR

        statuses = {}
        for job in cb_args["jobs"]:
            if job[0] != "S":
                statuses[job[1]["id"]] = job[0]
            else:
                statuses[job[1]["id"]] = \
                    cls.statustostr(job[1]["state"], job[1]["result"], True)
        return chk_status, statuses

    @classmethod
    def resulttostr(cls, resultid, singlechar=False):
        # if result not returned, just return empty string back
        inner = __import__("flux.core.inner", fromlist=["raw"])
        if resultid == "":
            return ""
        ret = inner.raw.flux_job_resulttostr(resultid, singlechar)
        return ret.decode("utf-8")

    @classmethod
    def statustostr(cls, stateid, resultid, abbrev=False):
        flux = __import__("flux", fromlist=["constants"])

        if stateid & flux.constants.FLUX_JOB_PENDING:
            statusstr = "PD" if abbrev else "PENDING"
        elif stateid & flux.constants.FLUX_JOB_RUNNING:
            statusstr = "R" if abbrev else "RUNNING"
        else:  # flux.constants.FLUX_JOB_INACTIVE
            statusstr = cls.resulttostr(resultid, abbrev)
        return cls.state(statusstr)

    @staticmethod
    def state(state):
        if state == "F":
            return State.FAILED
        elif state == "R":
            return State.RUNNING
        elif state == "PD":
            return State.PENDING
        elif state == "C":
            return State.CANCELLED
        else:
            return State.UNKNOWN
