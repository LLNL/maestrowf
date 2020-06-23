from abc import abstractclassmethod, abstractmethod, \
    abstractstaticmethod, ABCMeta


class FluxInterface(metaclass=ABCMeta):

    @abstractclassmethod
    def get_statuses(cls, handle, joblist):
        """
        Return the statuses from a given Flux handle and joblist.

        :param handle: An instance of a Flux handle to a running broker.
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

    @property
    @abstractmethod
    def key(self):
        """
        Return the key name for a ScriptAdapter.

        This is used to register the adapter in the ScriptAdapterFactory
        and when writing the workflow specification.

        :return: A string of the name of a FluxInterface class.
        """
