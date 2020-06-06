"""A module for utility classes to interface with Flux."""

from abc import ABC, abstractmethod


class FluxInterface(ABC):
    @abstractmethod
    def __init__(self, uri):
        pass

    @abstractmethod
    def get_statuses(self, joblist):
        pass
