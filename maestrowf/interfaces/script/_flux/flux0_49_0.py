import logging
from math import ceil
import os

from maestrowf.abstracts.enums import (
    CancelCode,
    JobStatusCode,
    State,
    StepPriority,
    SubmissionCode,
)
from maestrowf.abstracts.interfaces.flux import FluxInterface

import concurrent.futures

LOGGER = logging.getLogger(__name__)

try:
    import flux
except ImportError:
    LOGGER.info("Failed to import Flux. Continuing.")


class FluxInterface_0490(FluxInterface):
    # This utility class is for Flux 0.49.0
    key = "0.49.0"

    flux_handle = None
    _urgencies = {
        StepPriority.HELD: 0,
        StepPriority.MINIMAL: 1,
        StepPriority.LOW: 9,
        StepPriority.MEDIUM: 16,
        StepPriority.HIGH: 24,
        StepPriority.EXPEDITE: 31,
    }

    @classmethod
    def get_flux_urgency(cls, urgency) -> int:
        if isinstance(urgency, str):
            LOGGER.debug("Found string urgency: %s", urgency)
            urgency = StepPriority.from_str(urgency)

        if isinstance(urgency, StepPriority):
            LOGGER.debug("StepUrgency urgency of '%s' given..", urgency)
            return cls._urgencies[urgency]
        else:
            LOGGER.debug("Float urgency of '%s' given..", urgency)
            return ceil(float(urgency) * 31)

    @classmethod
    def submit(
        cls,
        nodes,
        procs,
        cores_per_task,
        path,
        cwd,
        walltime,
        ngpus=0,
        job_name=None,
        force_broker=True,
        urgency=StepPriority.MEDIUM,
        waitable=False
    ):
        try:
            # TODO: add better error handling/throwing in the class func
            # to enable more uniform detection/messaging when connection fails
            # to deal with both missing uri in allocations on non-flux machines
            cls.connect_to_flux()

            # NOTE: This previously placed everything under a broker. However,
            # if there's a job that schedules items to Flux, it will schedule
            # all new jobs to the sub-broker. Sometimes this is desired, but
            # it's incorrect to make that the general case. If we are asking
            # for a single node, don't use a broker -- but introduce a flag
            # that can force a single node to run in a broker.

            if force_broker:
                LOGGER.debug(
                    "Launch under Flux sub-broker. [force_broker=%s, "
                    "nodes=%d]",
                    force_broker,
                    nodes,
                )
                ngpus_per_slot = int(ceil(ngpus / nodes))
                jobspec = flux.job.JobspecV1.from_nest_command(
                    [path],
                    num_nodes=nodes,
                    cores_per_slot=cores_per_task,
                    num_slots=procs,
                    gpus_per_slot=ngpus_per_slot,
                )
            else:
                LOGGER.debug(
                    "Launch under root Flux broker. [force_broker=%s, "
                    "nodes=%d]",
                    force_broker,
                    nodes,
                )
                jobspec = flux.job.JobspecV1.from_command(
                    [path],
                    num_tasks=procs,
                    num_nodes=nodes,
                    cores_per_task=cores_per_task,
                    gpus_per_task=ngpus,
                )

            LOGGER.debug("Handle address -- %s", hex(id(cls.flux_handle)))
            if job_name:
                jobspec.setattr("system.job.name", job_name)
            jobspec.cwd = cwd
            jobspec.environment = dict(os.environ)

            if walltime > 0:
                jobspec.duration = walltime

            jobspec.stdout = f"{job_name}.{{{{id}}}}.out"
            jobspec.stderr = f"{job_name}.{{{{id}}}}.err"

            # Submit our job spec.
            jobid = flux.job.submit(
                cls.flux_handle, jobspec, waitable=waitable, urgency=urgency
            )
            submit_status = SubmissionCode.OK
            retcode = 0

            LOGGER.info(
                "Submission returned status OK. -- "
                "Assigned identifier (%s)",
                jobid,
            )

            # NOTE: cannot pickle JobID instances, so must store jobid's as
            # strings and reconstruct for use later. Also ensure we get the
            # Base58 form instead of integer for better user facing logging
            jobid = str(jobid.f58)

        except ConnectionResetError as exception:
            LOGGER.error("Submission failed -- Message (%s).",
                         exception,
                         exc_info=True)
            jobid = -1
            retcode = -2
            submit_status = SubmissionCode.ERROR
        except Exception as exception:
            LOGGER.error("Submission failed -- Message (%s).",
                         exception,
                         exc_info=True)
            jobid = -1
            retcode = -1
            submit_status = SubmissionCode.ERROR

        return jobid, retcode, submit_status

    @classmethod
    def bulk_submit(
        cls,
        job_specs,
    ):
        # TODO: add better error handling/throwing in the class func
        # to enable more uniform detection/messaging when connection fails
        # to deal with both missing uri in allocations on non-flux machines
        cls.connect_to_flux()

        # NOTE: This previously placed everything under a broker. However,
        # if there's a job that schedules items to Flux, it will schedule
        # all new jobs to the sub-broker. Sometimes this is desired, but
        # it's incorrect to make that the general case. If we are asking
        # for a single node, don't use a broker -- but introduce a flag
        # that can force a single node to run in a broker.

        with flux.job.FluxExecutor(threads=10) as executor:
            flux_job_specs = []
            for job_spec in job_specs:
                force_broker = job_spec['force_broker']
                nodes = job_spec['nodes']
                cores_per_task = job_spec['cores_per_task']
                procs = job_spec['processors']
                ngpus = job_spec['ngpus']
                waitable = job_spec['waitable']
                cwd = job_spec['cwd']
                path = job_spec['path']
                job_name = job_spec['stepid']
                walltime = job_spec['walltime']
                if force_broker:
                    LOGGER.debug(
                        "Launch under Flux sub-broker. [force_broker=%s, "
                        "nodes=%d]",
                        force_broker,
                        nodes,
                    )
                    ngpus_per_slot = int(ceil(ngpus / nodes))
                    jobspec = flux.job.JobspecV1.from_nest_command(
                        [path],
                        num_nodes=nodes,
                        cores_per_slot=cores_per_task,
                        num_slots=procs,
                        gpus_per_slot=ngpus_per_slot,
                    )
                else:
                    LOGGER.debug(
                        "Launch under root Flux broker. [force_broker=%s, "
                        "nodes=%d]",
                        force_broker,
                        nodes,
                    )
                    jobspec = flux.job.JobspecV1.from_command(
                        [path],
                        num_tasks=procs,
                        num_nodes=nodes,
                        cores_per_task=cores_per_task,
                        gpus_per_task=ngpus,
                    )

                LOGGER.debug("Handle address -- %s", hex(id(cls.flux_handle)))
                if job_name:
                    jobspec.setattr("system.job.name", job_name)
                jobspec.cwd = cwd
                jobspec.environment = dict(os.environ)

                if walltime > 0:
                    jobspec.duration = walltime

                jobspec.stdout = f"{job_name}.{{{{id}}}}.out"
                jobspec.stderr = f"{job_name}.{{{{id}}}}.err"

                flux_job_specs.append(jobspec)

            # for jname, js in zip(job_specs, flux_job_specs):
            #     print("Submitting jobs:")
            #     print(f"Name: {jname['stepid']}")
            #     print(js)
            # Submit our job spec.
            future_jobids = {executor.submit(fjspec, waitable=mjspec['waitable']): mjspec['stepid'] for fjspec, mjspec in zip(flux_job_specs, job_specs)}
            
            # jobid = executor.submit(
            #     cls.flux_handle, jobspec, waitable=waitable, urgency=urgency
            # )
            # for future_jobid, jobname in future_jobids.items():
            #     try:
            #         jobid_f58_tmp = flux.job.JobID(future_jobid.jobid(timeout=0.1)).f58
            #         print(f"step {jobname} recieved jobid {str(jobid_f58_tmp)}")
            #     except concurrent.futures.TimeoutError as cfte:
            #         jobid_f58_tmp = None
            #         print(f"step {jobname} hasn't recieved a jobid within the timeout of 0.1s")



            for future_jobid in concurrent.futures.as_completed(future_jobids):
                stepid = future_jobids[future_jobid]
                print(f"awaiting {stepid}")

                try:
                    jobid = future_jobid.result()
                    submit_status = SubmissionCode.OK
                    # LOGGER.info(
                    #     "Submission returned status OK. -- "
                    #     "Assigned identifier (%s)",
                    #     jobid,
                    # )
                    retcode = 0
                except flux.job.event.JobException as fje:
                    jobid = -1
                    submit_status = SubmissionCode.ERROR
                    retcode = 1
                    # LOGGER.error("Submission failed -- Message (%s).",
                    #              fje,
                    #              exc_info=True)
                    print(f"Error submitting job for step {stepid}: {fje.note}")

                # NOTE: cannot pickle JobID instances, so must store jobid's as
                # strings and reconstruct for use later. Also ensure we get the
                # Base58 form instead of integer for better user facing logging
                # print(f"jobid type: {type(jobid)}")
                jobid_f58 = flux.job.JobID(jobid).f58
                jobid = str(jobid_f58)

                yield jobid, retcode, submit_status

    @classmethod
    def bulk_submit_async(
        cls,
        job_specs,
        executor
    ):
        # TODO: add better error handling/throwing in the class func
        # to enable more uniform detection/messaging when connection fails
        # to deal with both missing uri in allocations on non-flux machines
        # cls.connect_to_flux()

        # NOTE: This previously placed everything under a broker. However,
        # if there's a job that schedules items to Flux, it will schedule
        # all new jobs to the sub-broker. Sometimes this is desired, but
        # it's incorrect to make that the general case. If we are asking
        # for a single node, don't use a broker -- but introduce a flag
        # that can force a single node to run in a broker.

        flux_job_specs = []
        for job_spec in job_specs:
            force_broker = job_spec['force_broker']
            nodes = job_spec['nodes']
            cores_per_task = job_spec['cores_per_task']
            procs = job_spec['processors']
            ngpus = job_spec['ngpus']
            waitable = job_spec['waitable']
            cwd = job_spec['cwd']
            path = job_spec['path']
            job_name = job_spec['stepid']
            walltime = job_spec['walltime']
            if force_broker:
                LOGGER.debug(
                    "Launch under Flux sub-broker. [force_broker=%s, "
                    "nodes=%d]",
                    force_broker,
                    nodes,
                )
                ngpus_per_slot = int(ceil(ngpus / nodes))
                jobspec = flux.job.JobspecV1.from_nest_command(
                    [path],
                    num_nodes=nodes,
                    cores_per_slot=cores_per_task,
                    num_slots=procs,
                    gpus_per_slot=ngpus_per_slot,
                )
            else:
                LOGGER.debug(
                    "Launch under root Flux broker. [force_broker=%s, "
                    "nodes=%d]",
                    force_broker,
                    nodes,
                )
                jobspec = flux.job.JobspecV1.from_command(
                    [path],
                    num_tasks=procs,
                    num_nodes=nodes,
                    cores_per_task=cores_per_task,
                    gpus_per_task=ngpus,
                )

            LOGGER.debug("Handle address -- %s", hex(id(cls.flux_handle)))
            if job_name:
                jobspec.setattr("system.job.name", job_name)
            jobspec.cwd = cwd
            jobspec.environment = dict(os.environ)

            if walltime > 0:
                jobspec.duration = walltime

            jobspec.stdout = f"{job_name}.{{{{id}}}}.out"
            jobspec.stderr = f"{job_name}.{{{{id}}}}.err"

            flux_job_specs.append(jobspec)

        # for jname, js in zip(job_specs, flux_job_specs):
        #     print("Submitting jobs:")
        #     print(f"Name: {jname['stepid']}")
        #     print(js)
        # Submit our job spec.
        future_jobids = {executor.submit(fjspec, waitable=mjspec['waitable']): mjspec['stepid'] for fjspec, mjspec in zip(flux_job_specs, job_specs)}
        print("Done submitting")
        # jobid = executor.submit(
        #     cls.flux_handle, jobspec, waitable=waitable, urgency=urgency
        # )
        # for future_jobid, jobname in future_jobids.items():
        #     try:
        #         jobid_f58_tmp = flux.job.JobID(future_jobid.jobid(timeout=0.1)).f58
        #         print(f"step {jobname} recieved jobid {str(jobid_f58_tmp)}")
        #     except concurrent.futures.TimeoutError as cfte:
        #         jobid_f58_tmp = None
        #         print(f"step {jobname} hasn't recieved a jobid within the timeout of 0.1s")

        # for future_jobid in concurrent.futures.as_completed(future_jobids):
        for future_jobid, stepid in future_jobids.items():
            # stepid = future_jobids[future_jobid]
            print(f"awaiting {stepid}")

            try:
                jobid = future_jobid.jobid() # future_jobid.result()

                # NOTE: might not need this with the executor?
                jobid_f58 = flux.job.JobID(jobid).f58
                jobid = str(jobid_f58)
                
                submit_status = SubmissionCode.OK
                LOGGER.info(
                    "Submission returned status OK. -- "
                    "Assigned identifier (%s)",
                    jobid,
                )
                retcode = 0
            except flux.job.event.JobException as fje:
                jobid = "-1"
                submit_status = SubmissionCode.ERROR
                retcode = 1
                LOGGER.error("Submission failed -- Message (%s).",
                             fje,
                             exc_info=True)
                print(f"Error submitting job for step {stepid}: {fje.note}")

            # NOTE: cannot pickle JobID instances, so must store jobid's as
            # strings and reconstruct for use later. Also ensure we get the
            # Base58 form instead of integer for better user facing logging
            # print(f"jobid type: {type(jobid)}")

            yield jobid, retcode, submit_status

    @classmethod
    def bulk_submit_async_mod(
        cls,
        job_specs,
        executor
    ):
        # TODO: add better error handling/throwing in the class func
        # to enable more uniform detection/messaging when connection fails
        # to deal with both missing uri in allocations on non-flux machines
        cls.connect_to_flux()

        # NOTE: This previously placed everything under a broker. However,
        # if there's a job that schedules items to Flux, it will schedule
        # all new jobs to the sub-broker. Sometimes this is desired, but
        # it's incorrect to make that the general case. If we are asking
        # for a single node, don't use a broker -- but introduce a flag
        # that can force a single node to run in a broker.
        
        for job_spec in job_specs:
            force_broker = job_spec['force_broker']
            nodes = job_spec['nodes']
            cores_per_task = job_spec['cores_per_task']
            procs = job_spec['processors']
            ngpus = job_spec['ngpus']
            waitable = job_spec['waitable']
            cwd = job_spec['cwd']
            path = job_spec['path']
            job_name = job_spec['stepid']
            walltime = job_spec['walltime']
            if force_broker:
                LOGGER.debug(
                    "Launch under Flux sub-broker. [force_broker=%s, "
                    "nodes=%d]",
                    force_broker,
                    nodes,
                )
                ngpus_per_slot = int(ceil(ngpus / nodes))
                jobspec = flux.job.JobspecV1.from_nest_command(
                    [path],
                    num_nodes=nodes,
                    cores_per_slot=cores_per_task,
                    num_slots=procs,
                    gpus_per_slot=ngpus_per_slot,
                )
            else:
                LOGGER.debug(
                    "Launch under root Flux broker. [force_broker=%s, "
                    "nodes=%d]",
                    force_broker,
                    nodes,
                )
                jobspec = flux.job.JobspecV1.from_command(
                    [path],
                    num_tasks=procs,
                    num_nodes=nodes,
                    cores_per_task=cores_per_task,
                    gpus_per_task=ngpus,
                )

            LOGGER.debug("Handle address -- %s", hex(id(cls.flux_handle)))
            if job_name:
                jobspec.setattr("system.job.name", job_name)
            jobspec.cwd = cwd
            jobspec.environment = dict(os.environ)

            if walltime > 0:
                jobspec.duration = walltime

            jobspec.stdout = f"{job_name}.{{{{id}}}}.out"
            jobspec.stderr = f"{job_name}.{{{{id}}}}.err"

            flux_job_specs.append(jobspec)

            def submit_callback(future: flux.job.submit.SubmitFuture,
                                flux_handle: flux.core.handle.Flux):
                jobid = future.get_id()

                result_future = flux.job.result_async(flux_handle, jobid)

                result_future.then(result_callback)

        future_jobids = {executor.submit(fjspec, waitable=mjspec['waitable']): mjspec['stepid'] for fjspec, mjspec in zip(flux_job_specs, job_specs)}

        # jobid = executor.submit(
        #     cls.flux_handle, jobspec, waitable=waitable, urgency=urgency
        # )
        # for future_jobid, jobname in future_jobids.items():
        #     try:
        #         jobid_f58_tmp = flux.job.JobID(future_jobid.jobid(timeout=0.1)).f58
        #         print(f"step {jobname} recieved jobid {str(jobid_f58_tmp)}")
        #     except concurrent.futures.TimeoutError as cfte:
        #         jobid_f58_tmp = None
        #         print(f"step {jobname} hasn't recieved a jobid within the timeout of 0.1s")



        for future_jobid in concurrent.futures.as_completed(future_jobids):
            stepid = future_jobids[future_jobid]
            print(f"awaiting {stepid}")

            try:
                jobid = future_jobid.result()
                submit_status = SubmissionCode.OK
                # LOGGER.info(
                #     "Submission returned status OK. -- "
                #     "Assigned identifier (%s)",
                #     jobid,
                # )
                retcode = 0
            except flux.job.event.JobException as fje:
                jobid = -1
                submit_status = SubmissionCode.ERROR
                retcode = 1
                # LOGGER.error("Submission failed -- Message (%s).",
                #              fje,
                #              exc_info=True)
                print(f"Error submitting job for step {stepid}: {fje.note}")

            # NOTE: cannot pickle JobID instances, so must store jobid's as
            # strings and reconstruct for use later. Also ensure we get the
            # Base58 form instead of integer for better user facing logging
            # print(f"jobid type: {type(jobid)}")
            jobid_f58 = flux.job.JobID(jobid).f58
            jobid = str(jobid_f58)

            yield jobid, retcode, submit_status

    @classmethod
    def parallelize(cls, procs, nodes=None, **kwargs):
        args = ["flux", "run", "-n", str(procs)]

        # if we've specified nodes, add that to wreckrun
        ntasks = nodes if nodes else 1
        args.append("-N")
        args.append(str(ntasks))

        if "cores per task" in kwargs:
            args.append("-c")
            # Error checking -> more comprehensive handling in base schedulerscriptadapter?
            if not kwargs["cores per task"]:
                cores_per_task = 1
            else:
                cores_per_task = kwargs["cores per task"]

            # args.append(str(kwargs["cores per task"]))
            args.append(str(cores_per_task))

            LOGGER.info("Adding 'cores per task' %s to flux args",
                        str(kwargs["cores per task"]))

        ngpus = kwargs.get("gpus", 0)
        if ngpus:
            gpus = str(ngpus)
            args.append("-g")
            args.append(gpus)

        # flux has additional arguments that can be passed via the '-o' flag.
        addtl = []
        addtl_args = kwargs.get("addtl_args", {})
        for key, value in addtl_args.items():
            addtl.append(f"{key}={value}")

        if addtl:
            args.append("-o")
            args.append(",".join(addtl))

        return " ".join(args)

    @classmethod
    def get_statuses(cls, joblist):
        # We need to import flux here, as it may not be installed on
        # all systems.
        cls.connect_to_flux()

        LOGGER.debug("Flux handle address -- %s", hex(id(cls.flux_handle)))

        # Reconstruct JobID instances from the str form of the Base58 id:
        # NOTE: cannot pickle JobID instances, so must store as strings and
        # reconstruct for use
        jobs_rpc = flux.job.list.JobList(
            cls.flux_handle,
            ids=[flux.job.JobID(jid) for jid in joblist])

        statuses = {}
        for jobinfo in jobs_rpc.jobs():
            LOGGER.debug(f"Checking status of job with id {str(jobinfo.id.f58)}")
            statuses[str(jobinfo.id.f58)] = cls.state(jobinfo.status_abbrev)

        chk_status = JobStatusCode.OK
        #  Print all errors accumulated in JobList RPC:
        try:
            for err in jobs_rpc.errors:
                chk_status = JobStatusCode.ERROR
                LOGGER.error("Error in JobList RPC %s", err)
        except EnvironmentError:
            pass

        return chk_status, statuses

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

        LOGGER.debug("Handle address -- %s", hex(id(cls.flux_handle)))
        LOGGER.debug(
            "Attempting to cancel jobs.\nJoblist:\n%s",
            "\n".join(str(j) for j in joblist),
        )

        # NOTE: cannot pickle JobID instances, so must store as strings and
        # reconstruct for use
        jobs_rpc = flux.job.list.JobList(
            cls.flux_handle,
            ids=[flux.job.JobID(jid) for jid in joblist])

        cancel_code = CancelCode.OK
        cancel_rcode = 0
        for job in jobs_rpc.jobs():
            try:
                LOGGER.debug("Cancelling Job %s...", str(job.id.f58))
                flux.job.cancel(cls.flux_handle, int(job.id))
            except Exception as exception:
                LOGGER.error("Job %s: %s", str(job.id.f58), str(exception))
                cancel_code = CancelCode.ERROR
                cancel_rcode = 1

        return cancel_code, cancel_rcode

    @staticmethod
    def state(state):
        if state == "D":        # Note this is actually short for DEPEND and is part of flux' pending virtual state
            return State.PENDING
        elif state == "S":      # Note this is short for SCHED and is also part of flux's pending virtual state
            return State.QUEUED
        elif state == "R":
            return State.RUNNING
        elif state == "C":
            return State.FINISHING
        elif state == "CD":
            return State.FINISHED
        elif state == "F":
            return State.FAILED
        elif state == "CA":
            return State.CANCELLED
        elif state == "TO":
            return State.TIMEDOUT
        else:
            LOGGER.error(f"Unhandled state: {state}")
            return State.UNKNOWN
