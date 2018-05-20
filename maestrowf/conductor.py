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

from maestrowf.datastructures.core import ExecutionGraph
from maestrowf.utils import create_parentdir

# Logger instantiation
rootlogger = logging.getLogger(inspect.getmodule(__name__))
logger = logging.getLogger(__name__)

# Formatting of logger.
LFORMAT = "%(asctime)s - %(name)s:%(funcName)s:%(lineno)s - " \
               "%(levelname)s - %(message)s"


def setup_argparser():
    """Set up the program's argument parser."""
    parser = ArgumentParser(prog="ExecutionManager",
                            description="An application for checking and "
                            "managing an ExecutionDAG within an executing"
                            "study.",
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument("directory", type=str, help="The directory where"
                        "a study has been set up and where a pickle file"
                        " of an ExecutionGraph is stored.")
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
                        help="Output logging to stdout in addition to a file.")
    parser.add_argument("-t", "--sleeptime", type=int, default=60,
                        help="Amount of time (in seconds) for the manager to "
                        "wait between job status checks.")

    return parser


def setup_logging(args, name):
    """
    Set up logging in the Main class.

    :param args: A Namespace object created by a parsed ArgumentParser.
    :param name: The name of the log file.
    """
    # Check if the user has specified a custom log path.
    if args.logpath:
        logger.info("Log path overwritten by command line -- %s",
                    args.logpath)
        log_path = args.logpath
    else:
        log_path = os.path.join(args.directory, "logs")

    loglevel = args.debug_lvl * 10

    # Attempt to create the logging directory.
    create_parentdir(log_path)
    formatter = logging.Formatter(LFORMAT)
    rootlogger.setLevel(loglevel)

    # Set up handlers
    if args.logstdout:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        rootlogger.addHandler(handler)

    log_file = os.path.join(log_path, "{}.log".format(name))
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    rootlogger.addHandler(handler)
    rootlogger.setLevel(loglevel)

    # Print the level of logging.
    logger.info("INFO Logging Level -- Enabled")
    logger.warning("WARNING Logging Level -- Enabled")
    logger.critical("CRITICAL Logging Level -- Enabled")
    logger.debug("DEBUG Logging Level -- Enabled")


def main():
    """Run the main segment of the conductor."""
    # Set up and parse the ArgumentParser
    parser = setup_argparser()
    args = parser.parse_args()

    # Unpickle the ExecutionGraph
    study_pkl = glob.glob(os.path.join(args.directory, "*.pkl"))
    # We expect only a single pickle file.
    if len(study_pkl) == 1:
        dag = ExecutionGraph.unpickle(study_pkl[0])
    else:
        if len(study_pkl) > 1:
            msg = "More than one pickle found. Expected only one. Aborting."
            status = 2
        else:
            msg = "No pickle found. Aborting."
            status = 1

        sys.stderr.write(msg)
        sys.exit(status)

    # Set up logging
    setup_logging(args, dag.name)
    # Use ExecutionGraph API to determine next jobs to be launched.
    logger.info("Checking the ExecutionGraph for study '%s' located in "
                "%s...", dag.name, study_pkl[0])
    logger.info("Study Description: %s", dag.description)

    cancel_lock_path = os.path.join(args.directory, ".cancel.lock")

    study_complete = False
    while not study_complete:
        if os.path.exists(cancel_lock_path):
            # cancel the study if a cancel lock file is found
            cancel_lock = FileLock(cancel_lock_path)
            try:
                with cancel_lock.acquire(timeout=10):
                    # we have the lock
                    dag.cancel_study()
                os.remove(cancel_lock_path)
                logger.info("Study '%s' has been cancelled.", dag.name)
            except Timeout:
                logger.error("Failed to acquire cancellation lock.")
                pass

        logger.info("Checking DAG status at %s", str(datetime.now()))
        # Execute steps that are ready
        study_complete = dag.execute_ready_steps()
        # Re-pickle the ExecutionGraph.
        dag.pickle(study_pkl[0])
        # Write out the state
        dag.write_status(os.path.split(study_pkl[0])[0])
        # Sleep for SLEEPTIME in args
        sleep(args.sleeptime)

    logger.info("Cleaning up...")
    dag.cleanup()
    logger.info("Squeaky clean!")

    # Explicitly return a 0 status.
    sys.exit(0)


if __name__ == "__main__":
    main()
