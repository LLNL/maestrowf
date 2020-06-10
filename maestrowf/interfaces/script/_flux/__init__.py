"""A module for utility classes to interface with Flux."""

from abc import ABC, abstractclassmethod


class FluxInterface(ABC):

    @abstractclassmethod
    def get_statuses(cls, handle, joblist):
        pass
