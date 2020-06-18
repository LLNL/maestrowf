from abc import abstractclassmethod, abstractmethod, ABCMeta


class FluxInterface(metaclass=ABCMeta):

    @abstractclassmethod
    def get_statuses(cls, handle, joblist):
        pass

    @property
    @abstractmethod
    def key(self):
        """
        Return the key name for a ScriptAdapter..

        This is used to register the adapter in the ScriptAdapterFactory
        and when writing the workflow specification.
        """
        pass

