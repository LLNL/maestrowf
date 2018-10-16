import logging
from threading import Lock


class ReadWriterLock(object):

    class _WriterWriter(object):
        def __init__(self, rwlock):
            self._rwlock = rwlock

        def release(self):
            self._wlock.release()

        @property
        def is_locked(self):
            return self._wlock.locked()

        def __enter__(self):
            return self.acquire()

        def __exit__(self, exc_type, exc_value, traceback):
            self._rwlock.release("writer")

    class _ReaderInterface(object):
        def __init__(self, rwlock):
            self._rwlock = rwlock

        def __enter__(self):
            return self.acquire()

        def __exit__(self, exc_type, exc_value, traceback):
            self._rwlock.release("reader")

    def __init__(self):
        # Information relevant for updating reader statuses.
        self._readers = 0
        self._read_lock = Lock()

        # Writer lock for exclusive writing.
        self._write_lock = Lock()

        # General information
        self._timeout = timeout

    def release(type):
        type = str(type).lower()

        if type == "reader":
            with self._read_lock:
                self._readers -= 1
        elif type == "writer":
            self._write_lock.release()
        else:
            msg = "A type other than reader or writer specified (type={})" \
                  .format(type)
            raise ValueError(msg)

    def acquire_write(self, timeout=-1. blocking=True):


    def acquire_read(self, timeout=-1, blocking=True):
        pass
