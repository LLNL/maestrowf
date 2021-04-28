###############################################################################
# Copyright (c) 2017, Lawrence Livermore National Security, LLC.
# Produced at the Lawrence Livermore National Laboratory
# Written by Francesco Di Natale, dinatale3@llnl.gov.
#
# LLNL-CODE-734340
# All rights reserved.
# This file is part of MaestroWF, Version: 1.0.0.
#
# For details, see https://github.com/LLNL/maestrowf.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################
"""A script for launching the Maestro conductor for study monitoring."""
from argparse import ArgumentParser, RawTextHelpFormatter
from filelock import FileLock, Timeout
from datetime import datetime
import glob
import inspect
import logging
import os
import sys
from time import sleep
import dill
import yaml

from maestrowf.abstracts.enums import StudyStatus
from maestrowf.datastructures.core import Study
from maestrowf.utils import create_parentdir, csvtable_to_dict, make_safe_path

# Logger instantiation
ROOTLOGGER = logging.getLogger(inspect.getmodule(__name__))
LOGGER = logging.getLogger(__name__)

# Formatting of logger.
LFORMAT = "%(asctime)s - %(name)s:%(funcName)s:%(lineno)s - " \
          "%(levelname)s - %(message)s"


def setup_logging(name, output_path, log_lvl=2, log_path=None,
                  log_stdout=False, log_format=None):
    """
    Set up logging in the Main class.
    :param args: A Namespace object created by a parsed ArgumentParser.
    :param name: The name of the log file.
    """
    # Check if the user has specified a custom log path.
    if log_path:
        LOGGER.info(
            "Log path overwritten by command line -- %s", log_path)
    else:
        log_path = os.path.join(output_path, "logs")

    if not log_format:
        log_format = LFORMAT

    loglevel = log_lvl * 10

    # Attempt to create the logging directory.
    create_parentdir(log_path)
    formatter = logging.Formatter(LFORMAT)
    ROOTLOGGER.setLevel(loglevel)

    # Set up handlers
    if log_stdout:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        ROOTLOGGER.addHandler(handler)

    log_file = os.path.join(log_path, "{}.log".format(name))
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    ROOTLOGGER.addHandler(handler)
    ROOTLOGGER.setLevel(loglevel)

    # Print the level of logging.
    LOGGER.info("INFO Logging Level -- Enabled")
    LOGGER.warning("WARNING Logging Level -- Enabled")
    LOGGER.critical("CRITICAL Logging Level -- Enabled")
    LOGGER.debug("DEBUG Logging Level -- Enabled")


def setup_parser():
    """
    Set up the Conductors's argument parser.

    :returns: A ArgumentParser that's initialized with the conductor's CLI.
    """

    # Set up the parser for our conductor here.
    parser = ArgumentParser(prog="Conductor",
                            description="An application for checking and "
                            "managing an ExecutionDAG within an executing "
                            "study.",
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument("directory", type=str, help="The directory where "
                        "a study has been set up and where a pickle file "
                        "of an ExecutionGraph is stored.")
    parser.add_argument("-s", "--status", action="store_true",
                        help="Check the status of the ExecutionGraph "
                        "located as specified by the 'directory' "
                        "argument.")
    parser.add_argument("-l", "--logpath", type=str,
                        help="Alternate path to store program logging.")
    parser.add_argument("-d", "--debug_lvl", type=int, default=2,
                        help="Level of logging messages to be output:\n"
                             "5 - Critical\n"
                             "4 - Error\n"
                             "3 - Warning\n"
                             "2 - Info (Default)\n"
                             "1 - Debug")
    parser.add_argument("-c", "--logstdout", action="store_true",
                        help="Output logging to stdout in addition to a "
                             "file.")
    parser.add_argument("-t", "--sleeptime", type=int, default=60,
                        help="Amount of time (in seconds) for the manager"
                             " to wait between job status checks.")

    return parser


class Conductor:
    """A class that provides an API for interacting with the Conductor."""

    _pkl_extension = ".study.pkl"
    _cancel_lock = ".cancel.lock"
    _batch_info = "batch.info"

    def __init__(self, study):
        """
        Create a new instance of a Conductor class.

        :param study: An instance of a populated Maestro study.
        """
        self._study = study
        self._setup = False

    @property
    def output_path(self):
        """
        Return the path representing the root of the study workspace.

        :returns: A string containing the path to the study's root.
        """
        return self._study.output_path

    @property
    def study_name(self):
        """
        Return the name of the study this Conductor instance is managing.

        :returns: A string containing the name of the study.
        """
        return self._study.name

    @classmethod
    def store_study(cls, study):
        """
        Store a Maestro study instance in a way the Conductor can read it.
        """
        # Pickle up the Study
        pkl_name = "{}{}".format(study.name, cls._pkl_extension)
        pkl_path = make_safe_path(study.output_path, pkl_name)
        study.pickle(pkl_path)

    @classmethod
    def load_batch(cls, out_path):
        """
        Load the batch information for the study rooted in 'out_path'.

        :param out_path: A string containing the path to a study root.
        :returns: A dict containing the batch information for the study.
        """
        batch_path = os.path.join(out_path, cls._batch_info)

        if not os.path.exists(batch_path):
            msg = "Batch info files is missing. Please re-run Maestro."
            LOGGER.error(msg)
            raise Exception(msg)

        with open(batch_path, 'r') as data:
            try:
                batch_info = yaml.load(data, yaml.FullLoader)
            except AttributeError:
                LOGGER.warning(
                    "*** PyYAML is using an unsafe version with a known "
                    "load vulnerability. Please upgrade your installation "
                    "to a more recent version! ***")
                batch_info = yaml.load(data)

        return batch_info

    @classmethod
    def store_batch(cls, out_path, batch):
        """
        Store the specified batch information to the study in 'out_path'.

        :param out_path: A string containing the patht to a study root.
        """
        path = os.path.join(out_path, cls._batch_info)
        with open(path, "wb") as batch_info:
            batch_info.write(yaml.dump(batch).encode("utf-8"))

    @classmethod
    def load_study(cls, out_path):
        """
        Load the Study instance in the study root specified by 'out_path'.

        :param out_path: A string containing the patht to a study root.
        :returns: A string containing the path to the study's root.
        """
        study_glob = \
            glob.glob(os.path.join(out_path, "*{}".format(cls._pkl_extension)))

        if len(study_glob) == 1:
            # We only expect one result.If we only get one, let's assume and
            # check after.
            path = study_glob[0]

            with open(path, 'rb') as pkl:
                obj = dill.load(pkl)

            if not isinstance(obj, Study):
                msg = \
                    "Object loaded from {path} is of type {type}. Expected " \
                    "an object of type '{cls}.'" \
                    .format(path=path, type=type(obj), cls=type(Study))
                LOGGER.error(msg)
                raise TypeError(msg)
        else:
            if len(study_glob) > 1:
                msg = "More than one pickle found. Expected one. Aborting."
            else:
                msg = "No pickle found. Aborting."

            msg = "Corrupted study directory found. {}".format(msg)
            raise Exception(msg)

        # Return the Study object
        return obj

    @classmethod
    def get_status(cls, output_path):
        """
        Retrieve the status of the study rooted at 'out_path'.

        :param out_path: A string containing the patht to a study root.
        :returns: A dictionary containing the status of the study.
        """
        stat_path = os.path.join(output_path, "status.csv")
        lock_path = os.path.join(output_path, ".status.lock")
        _ = {}
        if os.path.exists(stat_path):
            lock = FileLock(lock_path)
            try:
                with lock.acquire(timeout=10):
                    with open(stat_path, "r") as stat_file:
                        _ = csvtable_to_dict(stat_file)
            except Timeout:
                pass

        return _

    @classmethod
    def mark_cancelled(cls, output_path):
        """
        Mark the study rooted at 'out_path'.

        :param out_path: A string containing the patht to a study root.
        :returns: A dictionary containing the status of the study.
        """
        lock_path = make_safe_path(output_path, cls._cancel_lock)
        with open(lock_path, 'a'):
            os.utime(lock_path, None)

    def initialize(self, batch_info, sleeptime=60):
        """
        Initializes the Conductor instance based on the stored study.

        :param batch_info: A dict containing batch information.
        :param sleeptime: The amount of sleep time between polling loops
                          [Default: 60s].
        """
        # Set our conductor's sleep time.
        self.sleep_time = sleeptime
        # Stage the study.
        self._pkl_path, self._exec_dag = self._study.stage()
        # Write metadata
        self._exec_dag.set_adapter(batch_info)
        self._study.store_metadata()
        self._setup = True

    def monitor_study(self):
        """Monitor a running study."""
        if not self._setup:
            msg = \
                "Study '{}' located in '{}' not initialized. Initialize " \
                "study before calling launching. Aborting." \
                .format(self.study_name, self.output_path)
            LOGGER.error(msg)
            raise Exception(msg)

        # Set some fixed variables that monitor will use.
        cancel_lock_path = make_safe_path(self.output_path, self._cancel_lock)
        dag = self._exec_dag
        pkl_path = \
            os.path.join(self._pkl_path, "{}.pkl".format(self._study.name))
        sleep_time = self.sleep_time

        LOGGER.debug(
            "\n -------- Calling monitor study -------\n"
            "pkl path    = %s\n"
            "cancel path = %s\n"
            "sleep time  = %s\n"
            "------------------------------------------\n",
            pkl_path, cancel_lock_path, sleep_time)

        completion_status = StudyStatus.RUNNING
        while completion_status == StudyStatus.RUNNING:
            if os.path.exists(cancel_lock_path):
                # cancel the study if a cancel lock file is found
                cancel_lock = FileLock(cancel_lock_path)
                try:
                    with cancel_lock.acquire(timeout=10):
                        # we have the lock
                        dag.cancel_study()
                    os.remove(cancel_lock_path)
                    LOGGER.info("Study '%s' has been cancelled.", dag.name)
                except Timeout:
                    LOGGER.error("Failed to acquire cancellation lock.")
                    pass

            LOGGER.info("Checking DAG status at %s", str(datetime.now()))
            # Execute steps that are ready
            # Receives StudyStatus enum
            completion_status = dag.execute_ready_steps()
            # Re-pickle the ExecutionGraph.
            dag.pickle(pkl_path)
            # Write out the state
            dag.write_status(os.path.split(pkl_path)[0])
            # Sleep for SLEEPTIME in args if study not complete.
            if completion_status == StudyStatus.RUNNING:
                sleep(sleep_time)

        return completion_status

    def cleanup(self):
        self._exec_dag.cleanup()


def main():
    """Run the main segment of the conductor."""
    conductor = None

    try:
        # Parse the command line args and load the study.
        parser = setup_parser()
        args = parser.parse_args()
        study = Conductor.load_study(args.directory)
        setup_logging(study.name, args.directory, args.debug_lvl,
                      args.logpath, args.logstdout)
        batch_info = Conductor.load_batch(args.directory)

        conductor = Conductor(study)
        conductor.initialize(batch_info, args.sleeptime)
        completion_status = conductor.monitor_study()

        LOGGER.info("Study completed with state '%s'.", completion_status)
        sys.exit(completion_status.value)
    except Exception as e:
        LOGGER.error(e.args, exc_info=True)
        raise e
    finally:
        if conductor:
            LOGGER.info("Study exiting, cleaning up...")
            conductor.cleanup()
            LOGGER.info("Squeaky clean!")


if __name__ == "__main__":
    main()
