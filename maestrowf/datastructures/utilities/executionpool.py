"""A module for containing data structures for process pool management"""

import logging
from Queue import Queue
from threading import Event, Lock, Thread

from maestrowf.abstracts import Singleton
from maestrowf.utils import start_process


class ExecutionPool(Singleton, Thread):
    """A class that manages the execution of multiple processes."""

    def __init__(self, limit=0, env=None):
        # A map of process id to running process.
        self._status_reg = {}
        self._proc_queue = Queue()
        self._env = env

        # Events for controlling ExecutionPool threading.
        self._stop = Event()

    def queue_process(self, path, cwd=None):
        # Simply
        self._proc_queue.put((path, cwd))

    def poll_processes(self, pids):
        for entry in self._status_reg.items():
            pass

    def kill_processes(self, pids):
        pass

    def stop(self):
        self._stop.set()

    def run(self):
        pass
