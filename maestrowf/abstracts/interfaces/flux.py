from abc import ABC, abstractclassmethod, abstractmethod, abstractstaticmethod


class FluxInterface(ABC):
    """ """

    @abstractclassmethod
    def get_statuses(cls, joblist):
        """Return the statuses from a given Flux handle and joblist.

        Args:
          joblist: A list of jobs to check the status of.

        Returns:
          A dictionary of job identifiers to statuses.

        """

    @abstractstaticmethod
    def state(state):
        """Map a scheduler specific job state to a Study.State enum.

        Args:
          adapter: Instance of a FluxAdapter
          state: A string of the state returned by Flux

        Returns:
          The mapped Study.State enumeration

        """

    @abstractclassmethod
    def parallelize(cls, procs, nodes=None, **kwargs):
        """Create a parallelized Flux command for launching.

        Args:
          procs: Number of processors to use.
          nodes: Number of nodes the parallel call will span.
            (Default value = None)
          kwargs: Extra keyword arguments.
          **kwargs:

        Returns:
          A string of a Flux MPI command.

        """

    @abstractclassmethod
    def submit(
        cls,
        nodes,
        procs,
        cores_per_task,
        path,
        cwd,
        walltime,
        npgus=0,
        job_name=None,
        force_broker=False,
    ):
        """Submit a job using this Flux interface's submit API.

        Args:
          nodes: The number of nodes to request on submission.
          procs: The number of cores to request on submission.
          cores_per_task: The number of cores per MPI task.
          path: Path to the script to be submitted.
          cwd: Path to the workspace to execute the script in.
          walltime: HH:MM:SS formatted time string for job duration.
          ngpus: The number of GPUs to request on submission.
          job_name: A name string to assign the submitted job.
            (Default value = None)
          force_broker: Forces the script to run under a Flux sub-broker.
            (Default value = False)
          npgus:  (Default value = 0)

        Returns:
          A string representing the jobid returned by Flux submit.

        """

    @abstractclassmethod
    def cancel(cls, joblist):
        """Cancel a job using this Flux interface's cancellation API.

        Args:
          joblist: A list of job identifiers to cancel.

        Returns:
          CancelCode enumeration that reflects result of cancellation.

        """

    @property
    @abstractmethod
    def key(self):
        """

        Args:

        Returns:
          This is used to register the adapter in the ScriptAdapterFactory
          and when writing the workflow specification.

          :return: A string of the name of a FluxInterface class.

        """
