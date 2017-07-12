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

"""A script for launching a YAML study specification."""
from argparse import ArgumentParser, RawTextHelpFormatter
import inspect
import logging
import os
import shutil
from subprocess import Popen, PIPE
import sys

from maestrowf.datastructures import YAMLSpecification
from maestrowf.datastructures.core import Study
from maestrowf.interfaces import SlurmScriptAdapter
from maestrowf.utils import create_parentdir


# Program Globals
ROOTLOGGER = logging.getLogger(inspect.getmodule(__name__))
LOGGER = logging.getLogger(__name__)

# Configuration globals
LFORMAT = "%(asctime)s - %(name)s:%(funcName)s:%(lineno)s - " \
          "%(levelname)s - %(message)s"
ACCEPTED_INPUT = set(["yes", "y"])


def setup_argparser():
    """
    Method for setting up the program's argument parser.
    """

    parser = ArgumentParser(prog="MaestroWF",
                            description="The Maestro Workflow Conductor for "
                            "specifiying, launching, and managing general "
                            "workflows.",
                            formatter_class=RawTextHelpFormatter)

    parser.add_argument("specification", type=str, help="The path to a Study"
                        " YAML specification that will be loaded and "
                        "executed.")
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
                        help="Log to stdout in addition to a file.")
    parser.add_argument("-t", "--sleeptime", type=int, default=60,
                        help="Amount of time (in seconds) for the manager to "
                        "wait between job status checks.")
    parser.add_argument("-y", "--autoyes", action="store_true", default=False,
                        help="Automatically answer yes to input prompts.")

    return parser


def setup_logging(args, path, name):
    """
    Utility method to set up logging based on the ArgumentParser.

    :param args: A Namespace object created by a parsed ArgumentParser.
    :param path: A default path to be used if a log path is not specified by
    user command line arguments.
    :param name: The name of the log file.
    """
    # If the user has specified a path, use that.
    if args.logpath:
        logpath = args.logpath
    # Otherwise, we should just output to the OUTPUT_PATH.
    else:
        logpath = os.path.join(path, "logs")

    loglevel = args.debug_lvl * 10

    # Create the FileHandler and add it to the logger.
    create_parentdir(logpath)
    formatter = logging.Formatter(LFORMAT)
    ROOTLOGGER.setLevel(loglevel)

    logname = "{}.log".format(name)
    fh = logging.FileHandler(os.path.join(logpath, logname))
    fh.setLevel(loglevel)
    fh.setFormatter(formatter)
    ROOTLOGGER.addHandler(fh)

    if args.logstdout:
        # Add the StreamHandler
        sh = logging.StreamHandler()
        sh.setLevel(loglevel)
        sh.setFormatter(formatter)
        ROOTLOGGER.addHandler(sh)

    # Print the level of logging.
    LOGGER.info("INFO Logging Level -- Enabled")
    LOGGER.warning("WARNING Logging Level -- Enabled")
    LOGGER.critical("CRITICAL Logging Level -- Enabled")
    LOGGER.debug("DEBUG Logging Level -- Enabled")


def main():
    """
    The launcher main function.

    This function uses command line arguments to locate the study description.
    It makes use of the maestrowf core data structures as a high level class
    inerface.
    """

    # Set up the necessary base data structures to begin study set up.
    parser = setup_argparser()
    args = parser.parse_args()

    # Load the Specification
    spec = YAMLSpecification.load_specification(args.specification)
    environment = spec.get_study_environment()
    parameters = spec.get_parameters()
    steps = spec.get_study_steps()

    # Setup the study.
    study = Study(spec.name, spec.description, studyenv=environment,
                  parameters=parameters, steps=steps)
    study.setup()
    setup_logging(args, study.output_path, study.name)

    # Stage the study.
    path, exec_dag = study.stage()

    # TODO: fdinatal - A factory class for adapters needs to be written. For
    # now, assuming SLURM but that'll be changed in the future.
    # Get the adapter specified and add it to the ExecutionGraph.
    adapter = SlurmScriptAdapter(**spec.batch)
    exec_dag.set_adapter(adapter)

    # Copy the spec to the output directory
    shutil.copy(args.specification, path)

    # Generate scripts
    exec_dag.generate_scripts()
    exec_dag.pickle(os.path.join(path, "{}.pkl".format(study.name)))

    # If we are automatically launching, just set the input as yes.
    if args.autoyes:
        uinput = "y"
    else:
        uinput = raw_input("Would you like to launch the study?[yn] ")

    if uinput.lower() in ACCEPTED_INPUT:
        # Launch manager with nohup
        cmd = ["nohup", "conductor",
               "-t", str(args.sleeptime),
               "-d", str(args.debug_lvl),
               path,
               "&>", "{}.txt".format(os.path.join(
                study.output_path, exec_dag.name))]
        LOGGER.debug(" ".join(cmd))
        Popen(" ".join(cmd), shell=True, stdout=PIPE, stderr=PIPE)

    sys.exit(0)


if __name__ == "__main__":
    main()
