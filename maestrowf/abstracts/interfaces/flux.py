from abc import ABC, abstractmethod
import logging

from maestrowf.abstracts.enums import StepPriority

LOGGER = logging.getLogger(__name__)

try:
    import flux
except ImportError:
    LOGGER.info("Failed to import Flux. Continuing.")


class FluxInterface(ABC):

    @classmethod
    def connect_to_flux(cls):
        if not cls.flux_handle:
            cls.flux_handle = flux.Flux()
            LOGGER.debug("New Flux handle created.")
            broker_version = cls.flux_handle.attr_get("version")
            adaptor_version = cls.key
            LOGGER.debug(
                "Connected to Flux broker running version %s using Maestro "
                "adapter version %s.", broker_version, adaptor_version)
            try:
                from distutils.version import StrictVersion
                adaptor_version = StrictVersion(adaptor_version)
                broker_version = StrictVersion(broker_version)
                if adaptor_version > broker_version:
                    LOGGER.error(
                        "Maestro adapter version (%s) is too new for the Flux "
                        "broker version (%s). Functionality not present in "
                        "this Flux version may be required by the adapter and "
                        "cause errors. Please switch to an older adapter.",
                        adaptor_version, broker_version
                    )
                elif adaptor_version < broker_version:
                    LOGGER.debug(
                        "Maestro adaptor version (%s) is older than the Flux "
                        "broker version (%s). This is usually OK, but if a "
                        "newer Maestro adapter is available, please consider "
                        "upgrading to maximize performance and compatibility.",
                        adaptor_version, broker_version
                    )
            except ImportError:
                pass

    @classmethod
    @abstractmethod
    def get_flux_urgency(cls, urgency) -> int:
        """
        Map a fixed enumeration or floating point priority to a Flux urgency.

        :param priority: Float or StepPriority enum representing priorty.
        :returns: An integery mapping the urgency parameter to a Flux urgency.
        """
        raise NotImplementedError()

    @classmethod
    @abstractmethod
    def get_statuses(cls, joblist):
        """
        Return the statuses from a given Flux handle and joblist.

        :param joblist: A list of jobs to check the status of.
        :return: A dictionary of job identifiers to statuses.
        """
        ...

    @classmethod
    @abstractmethod
    def state(state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param adapter: Instance of a FluxAdapter
        :param state: A string of the state returned by Flux
        :return: The mapped Study.State enumeration
        """
        ...

    @classmethod
    @abstractmethod
    def parallelize(cls, procs, nodes=None, **kwargs):
        """
        Create a parallelized Flux command for launching.

        :param procs: Number of processors to use.
        :param nodes: Number of nodes the parallel call will span.
        :param kwargs: Extra keyword arguments.
        :return: A string of a Flux MPI command.
        """
        ...

    @classmethod
    @abstractmethod
    def submit(
        cls, nodes, procs, cores_per_task, path, cwd, walltime,
        npgus=0, job_name=None, force_broker=False, urgency=StepPriority.MEDIUM
    ):
        """
        Submit a job using this Flux interface's submit API.

        :param nodes: The number of nodes to request on submission.
        :param procs: The number of cores to request on submission.
        :param cores_per_task: The number of cores per MPI task.
        :param path: Path to the script to be submitted.
        :param cwd: Path to the workspace to execute the script in.
        :param walltime: HH:MM:SS formatted time string for job duration.
        :param ngpus: The number of GPUs to request on submission.
        :param job_name: A name string to assign the submitted job.
        :param force_broker: Forces the script to run under a Flux sub-broker.
        :param urgency: Enumerated scheduling priority for the submitted job.
        :return: A string representing the jobid returned by Flux submit.
        :return: An integer of the return code submission returned.
        :return: SubmissionCode enumeration that reflects result of submission.
        """
        ...

    @classmethod
    @abstractmethod
    def cancel(cls, joblist):
        """
        Cancel a job using this Flux interface's cancellation API.

        :param joblist: A list of job identifiers to cancel.
        :return: CancelCode enumeration that reflects result of cancellation.
        """
        ...

    @property
    @abstractmethod
    def key(self):
        """
        Return the key name for a ScriptAdapter.

        This is used to register the adapter in the ScriptAdapterFactory
        and when writing the workflow specification.

        :return: A string of the name of a FluxInterface class.
        """
        ...
