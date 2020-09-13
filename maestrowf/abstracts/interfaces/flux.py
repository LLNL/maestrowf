from abc import ABC, abstractclassmethod, abstractmethod, \
    abstractstaticmethod

from maestrowf.abstracts import Singleton


class FluxInterface(Singleton, ABC):

    @abstractclassmethod
    def get_statuses(cls, joblist):
        """
        Return the statuses from a given Flux handle and joblist.

        :param joblist: A list of jobs to check the status of.
        :return: A dictionary of job identifiers to statuses.
        """

    @abstractstaticmethod
    def state(state):
        """
        Map a scheduler specific job state to a Study.State enum.

        :param adapter: Instance of a FluxAdapter
        :param state: A string of the state returned by Flux
        :return: The mapped Study.State enumeration
        """

    @abstractclassmethod
    def parallelize(cls, procs, nodes=None, **kwargs):
        """
        Create a parallelized Flux command for launching.

        :param procs: Number of processors to use.
        :param nodes: Number of nodes the parallel call will span.
        :param kwargs: Extra keyword arguments.
        :return: A string of a Flux MPI command.
        """

    @abstractclassmethod
    def submit(cls, nodes, procs, cores_per_task, path, cwd, npgus=0):
        """
        Submit a job using this Flux interface's submit API.

        :param nodes: The number of nodes to request on submission.
        :param procs: The number of cores to request on submission.
        :param cores_per_task: The number of cores per MPI task.
        :param path: Path to the script to be submitted.
        :param cwd: Path to the workspace to execute the script in.
        :param ngpus: The number of GPUs to request on submission.
        :return: A string representing the jobid returned by Flux submit.
        :return: An integer of the return code submission returned.
        :return: SubmissionCode enumeration that reflects result of submission.
        """

    @property
    @abstractmethod
    def key(self):
        """
        Return the key name for a ScriptAdapter.

        This is used to register the adapter in the ScriptAdapterFactory
        and when writing the workflow specification.

        :return: A string of the name of a FluxInterface class.
        """
