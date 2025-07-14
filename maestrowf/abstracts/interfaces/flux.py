from abc import ABC, abstractmethod
import getpass
import json
import logging

from maestrowf.abstracts.enums import StepPriority
from maestrowf.utils import parse_version

from packaging.version import InvalidVersion

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
            broker_version_str = cls.flux_handle.attr_get("version")
            adaptor_version_str = cls.key
            LOGGER.debug(
                "Connected to Flux broker running version %s using Maestro "
                "adapter version %s.", broker_version_str, adaptor_version_str)

            versions_parsed = True
            try:
                # from distutils.version import StrictVersion
                # adaptor_version = StrictVersion(adaptor_version)
                # broker_version = StrictVersion(broker_version)
                adaptor_version = parse_version(adaptor_version_str)
            except InvalidVersion:
                LOGGER.warning("Could not parse flux adaptor version '%s'."
                               "May experience unexpected behavior.",
                               adaptor_version_str)
                versions_parsed = False
                
            try:
                broker_version = parse_version(broker_version_str)
            except InvalidVersion:
                LOGGER.warning("Could not parse flux broker version '%s'."
                               "May experience unexpected behavior.",
                               broker_version_str)
                versions_parsed = False

            if not versions_parsed:
                return

            if adaptor_version.base_version > broker_version.base_version:
                LOGGER.error(
                    "Maestro adapter version (%s) is too new for the Flux "
                    "broker version (%s). Functionality not present in "
                    "this Flux version may be required by the adapter and "
                    "cause errors. Please switch to an older adapter.",
                    adaptor_version, broker_version
                )
            elif adaptor_version.base_version < broker_version.base_version:
                LOGGER.debug(
                    "Maestro adaptor version (%s) is older than the Flux "
                    "broker version (%s). This is usually OK, but if a "
                    "newer Maestro adapter is available, please consider "
                    "upgrading to maximize performance and compatibility.",
                    adaptor_version, broker_version
                )
            # TODO: add custom version object to more properly handle dev
            #       and prerelease versions for both semver and pep440 version
            #       schemes.  Then add log message reflecting it if detected

    @classmethod
    def get_flux_version(cls):
        cls.connect_to_flux()
        # from distutils.version import StrictVersion
        # return StrictVersion(cls.flux_handle.attr_get("version"))
        # return parse_version(cls.flux_handle.attr_get("version"))
        return cls.flux_handle.attr_get("version")

    @classmethod
    def get_broker_queues(cls):
        """
        Use flux's rpc interface to get available queues to submit to.
        Current (~0.74) flux behavior for nested brokers' is to only have an
        anonymous queue without explicit user configuration to create some.

        Todo: locate flux version where queue support was added in case not all
        adapters can support it.
        """
        cls.connect_to_flux()
        queue_config = cls.flux_handle.rpc("config.get").get().get("queues", {})
        return list(queue_config.keys())

    @classmethod
    def get_broker_user_banks(cls):
        """
        Use flux's rpc interface to get available banks for current user.
        Current (~0.74) flux behavior for nested brokers' is to not have
        accounting plugin active.

        Todo: locate flux version where accounting was available
        """
        cls.connect_to_flux()
        username = getpass.getuser()
        try:
            banks = cls.flux_handle.rpc("accounting.view_user",
                                        {"list_banks": True,
                                         "username": username,
                                         "parsable": True,  # Mandatory in 0.75?
                                         "format": ""}).get()
        except OSError as be:
            if '[Errno 38] No service matching accounting.view_user is registered' not in str(be):
                raise           # If some other unexpected error raise it
            banks = ""

        # rpc call returns single string: 'bank1\nbank2\nbank3\n'
        bank_list = banks['view_user'].split('\n')
        return bank_list

    @classmethod
    def get_broker_all_banks(cls):
        """
        Use flux's rpc interface to get all available banks on this machine.
        Current (~0.74) flux behavior for nested brokers' is to not have
        accounting plugin active.
        """
        cls.connect_to_flux()
        try:
            banks = cls.flux_handle.rpc("accounting.list_banks",
                                        {"inactive": True,
                                         "table": False,
                                         "json": True,  # Default in 0.75 is no longer json
                                         "fields": "bank",
                                         "format": ""}).get()
        except OSError as be:
            if '[Errno 38] No service matching accounting.list_banks is registered' not in str(be):
                raise           # If some other unexpected error raise it
            banks = "[{}]"

        # rpc call returns list of banks as json string
        bank_dicts = json.loads(banks['list_banks'])

        return [bdict['bank'] for bdict in bank_dicts]

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
