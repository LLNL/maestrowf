import errno
import logging

import flux
import flux.job
import flux.constants
from flux.core.inner import raw
from . import FluxInterface

LOGGER = logging.getLogger(__name__)


class FluxInterface_0160(FluxInterface):
    key = "0.16.0"

    STATE_CONST_DICT = {
        "depend": flux.constants.FLUX_JOB_DEPEND,
        "sched": flux.constants.FLUX_JOB_SCHED,
        "run": flux.constants.FLUX_JOB_RUN,
        "cleanup": flux.constants.FLUX_JOB_CLEANUP,
        "inactive": flux.constants.FLUX_JOB_INACTIVE,
        "pending": flux.constants.FLUX_JOB_PENDING,
        "running": flux.constants.FLUX_JOB_RUNNING,
        "active": flux.constants.FLUX_JOB_ACTIVE,
    }

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
        cb_args = {
            "jobs":   [],
            "handle": handle,
            "count":  0,
            "total": len(joblist),
        }

        for jobid in joblist:
            rpc_handle = flux.job.job_list_id(handle, jobid, list(cls.attrs))
            rpc_handle.then(cls.status_callback, arg=(jobid, cb_args))
        ret = handle.reactor_run(rpc_handle.get_reactor(), 0)

        statuses = {}
        for job in cb_args["jobs"]:
            if job[0] != "S":
                statuses[job[1]["id"]] = job[0]
            else:
                statuses[job[1]["id"]] = \
                    cls.statustostr(job[1]["state"], job[1]["result"], True)
        return ret, statuses

    @classmethod
    def resulttostr(cls, resultid, singlechar=False):
        # if result not returned, just return empty string back
        if resultid == "":
            return ""
        return raw.flux_job_resulttostr(resultid, singlechar).decode("utf-8")

    @classmethod
    def statustostr(cls, stateid, resultid, abbrev=False):
        if stateid & flux.constants.FLUX_JOB_PENDING:
            statusstr = "PD" if abbrev else "PENDING"
        elif stateid & flux.constants.FLUX_JOB_RUNNING:
            statusstr = "R" if abbrev else "RUNNING"
        else:  # flux.constants.FLUX_JOB_INACTIVE
            statusstr = cls.resulttostr(resultid, abbrev)
        return statusstr
