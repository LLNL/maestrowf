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
from argparse import ArgumentParser, ArgumentError, RawTextHelpFormatter
from filelock import FileLock, Timeout
import inspect
import logging
import os
import shutil
from subprocess import Popen, PIPE
import six
import sys
import tabulate
import time

from maestrowf.datastructures import YAMLSpecification
from maestrowf.datastructures.core import Study
from maestrowf.datastructures.environment import Variable
from maestrowf.utils import create_parentdir, csvtable_to_dict, make_safe_path


# Program Globals
ROOTLOGGER = logging.getLogger(inspect.getmodule(__name__))
LOGGER = logging.getLogger(__name__)

# Configuration globals
LFORMAT = "%(asctime)s - %(name)s:%(funcName)s:%(lineno)s - " \
          "%(levelname)s - %(message)s"
ACCEPTED_INPUT = set(["yes", "y"])


def status_study(args):
    """Check and print the status of an executing study."""
    study_path = args.directory
    stat_path = os.path.join(study_path, "status.csv")
    lock_path = os.path.join(study_path, ".status.lock")
    if os.path.exists(stat_path):
        lock = FileLock(lock_path)
        try:
            with lock.acquire(timeout=10):
                with open(stat_path, "r") as stat_file:
                    _ = csvtable_to_dict(stat_file)
                    print(tabulate.tabulate(_, headers="keys"))
        except Timeout:
            pass

    return 0


def cancel_study(args):
    """Flag a study to be cancelled."""
    if not os.path.isdir(args.directory):
        return 1

    lock_path = os.path.join(args.directory, ".cancel.lock")

    with open(lock_path, 'a'):
        os.utime(lock_path, None)

    return 0


def run_study(args):
    """Run a Maestro study."""
    # Load the Specification
    spec = YAMLSpecification.load_specification(args.specification)
    environment = spec.get_study_environment()
    parameters = spec.get_parameters()
    steps = spec.get_study_steps()

    # Set up the output directory.
    out_dir = environment.remove("OUTPUT_PATH")
    if out_dir is None:
        # If we don't find OUTPUT_PATH in the environment, assume pwd.
        out_dir = os.path.abspath("./")
    else:
        # We just take the value from the environment.
        out_dir = os.path.abspath(out_dir.value)

    out_name = "{}_{}".format(
        spec.name.replace(" ", "_"),
        time.strftime("%Y%m%d-%H%M%S")
    )
    output_path = make_safe_path(out_dir, out_name)

    # Now that we know outpath, set up logging.
    setup_logging(args, output_path, spec.name)

    # Addition of the $(SPECROOT) to the environment.
    spec_root = os.path.split(args.specification)[0]
    spec_root = Variable("SPECROOT", os.path.abspath(spec_root))
    environment.add(spec_root)

    # Setup the study.
    study = Study(spec.name, spec.description, studyenv=environment,
                  parameters=parameters, steps=steps, out_path=output_path)

    # Check if the submission attempts is greater than 0:
    if args.attempts < 1:
        _msg = "Submission attempts must be greater than 0. " \
               "'{}' provided.".format(args.attempts)
        LOGGER.error(_msg)
        raise ArgumentError(_msg)

    # Check if the throttle is zero or greater:
    if args.throttle < 0:
        _msg = "Submission throttle must be a value of zero or greater. " \
               "'{}' provided.".format(args.throttle)
        LOGGER.error(_msg)
        raise ArgumentError(_msg)

    # Check if the restart limit is zero or greater:
    if args.rlimit < 0:
        _msg = "Restart limit must be a value of zero or greater. " \
               "'{}' provided.".format(args.rlimit)
        LOGGER.error(_msg)
        raise ArgumentError(_msg)

    study.setup(
        throttle=args.throttle,
        submission_attempts=args.attempts,
        restart_limit=args.rlimit,
        use_tmp=args.usetmp
    )

    # Stage the study.
    path, exec_dag = study.stage()

    if not spec.batch:
        exec_dag.set_adapter({"type": "local"})
    else:
        exec_dag.set_adapter(spec.batch)

    # Copy the spec to the output directory
    shutil.copy(args.specification, path)

    # Check for a dry run
    if args.dryrun:
        raise NotImplementedError("The 'dryrun' mode is in development.")

    # Pickle up the DAG
    exec_dag.pickle(os.path.join(path, "{}.pkl".format(study.name)))

    # If we are automatically launching, just set the input as yes.
    if args.autoyes:
        uinput = "y"
    elif args.autono:
        uinput = "n"
    else:
        uinput = six.moves.input("Would you like to launch the study?[yn] ")

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

    return 0


def setup_argparser():
    """Set up the program's argument parser."""
    parser = ArgumentParser(
        prog="maestro",
        description="The Maestro Workflow Conductor for specifiying, launching"
        ", and managing general workflows.",
        formatter_class=RawTextHelpFormatter)
    subparsers = parser.add_subparsers(dest='subparser')

    # subparser for a cancel subcommand
    cancel = subparsers.add_parser(
        'cancel',
        help="Cancel all running jobs.")
    cancel.add_argument(
        "directory", type=str,
        help="Directory containing a launched study.")
    cancel.set_defaults(func=cancel_study)

    # subparser for a run subcommand
    run = subparsers.add_parser('run',
                                help="Launch a study based on a specification")
    run.add_argument("-a", "--attempts", type=int, default=1,
                     help="Maximum number of submission attempts before a "
                     "step is marked as failed. [Default: %(default)d]")
    run.add_argument("-r", "--rlimit", type=int, default=1,
                     help="Maximum number of restarts allowed when steps."
                     "specify a restart command (0 denotes no limit). "
                     "[Default: %(default)d]")
    run.add_argument("-t", "--throttle", type=int, default=0,
                     help="Maximum number of inflight jobs allowed to execute "
                     "simultaneously (0 denotes not throttling)."
                     "[Default: %(default)d]")
    run.add_argument("-s", "--sleeptime", type=int, default=60,
                     help="Amount of time (in seconds) for the manager to "
                     "wait between job status checks. [Default: %(default)d]")
    run.add_argument("-d", "--dryrun", action="store_true", default=False,
                     help="Generate the directory structure and scripts for a "
                     "study but do not launch it. [Default: %(default)s]")

    prompt_opts = run.add_mutually_exclusive_group()
    prompt_opts.add_argument(
        "-n", "--autono", action="store_true", default=False,
        help="Automatically answer no to input prompts.")
    prompt_opts.add_argument(
        "-y", "--autoyes", action="store_true", default=False,
        help="Automatically answer yes to input prompts.")

    # The only required positional argument for 'run' is a specification path.
    run.add_argument(
        "specification", type=str,
        help="The path to a Study YAML specification that will be loaded and "
        "executed.")
    run.add_argument(
        "--usetmp", action="store_true", default=False,
        help="Make use of a temporary directory for dumping scripts and other "
        "Maestro related files.")
    run.set_defaults(func=run_study)

    # subparser for a status subcommand
    status = subparsers.add_parser(
        'status',
        help="Check the status of a running study.")
    status.add_argument(
        "directory", type=str,
        help="Directory containing a launched study.")
    status.set_defaults(func=status_study)

    # global options
    parser.add_argument(
        "-l", "--logpath", type=str,
        help="Alternate path to store program logging.")
    parser.add_argument(
        "-d", "--debug_lvl", type=int, default=2,
        help="Level of logging messages to be output:\n"
        "5 - Critical\n"
        "4 - Error\n"
        "3 - Warning\n"
        "2 - Info (Default)\n"
        "1 - Debug")
    parser.add_argument(
        "-c", "--logstdout", action="store_true", default=True,
        help="Log to stdout in addition to a file. [Default: %(default)s]")

    return parser


def setup_logging(args, path, name):
    """
    Set up logging based on the ArgumentParser.

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
        logpath = make_safe_path(path, "logs")

    loglevel = args.debug_lvl * 10

    # Create the FileHandler and add it to the logger.
    create_parentdir(logpath)
    formatter = logging.Formatter(LFORMAT)
    ROOTLOGGER.setLevel(loglevel)

    logname = make_safe_path("{}.log".format(name))
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
    Execute the main program's functionality.

    This function uses command line arguments to locate the study description.
    It makes use of the maestrowf core data structures as a high level class
    inerface.
    """
    # Set up the necessary base data structures to begin study set up.
    parser = setup_argparser()
    args = parser.parse_args()

    rc = args.func(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
