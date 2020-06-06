import flux
from . import FluxInterface


class FluxInterface_0160(FluxInterface):
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

    def __init__(self, uri):
        self.flux = flux.Flux(uri)
