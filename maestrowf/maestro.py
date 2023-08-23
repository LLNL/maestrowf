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
import jsonschema
import logging
import os
import shutil
import six
import sys
# import tabulate
import time

from maestrowf import __version__, status_renderer_factory
from maestrowf.conductor import Conductor
from maestrowf.specification import YAMLSpecification
from maestrowf.datastructures.core import Study
from maestrowf.datastructures.environment import Variable
from maestrowf.utils import \
    create_parentdir, create_dictionary, LoggerUtility, make_safe_path, \
    start_process


# Program Globals
LOGGER = logging.getLogger(__name__)
LOG_UTIL = LoggerUtility(LOGGER)

# Configuration globals
DEBUG_FORMAT = "[%(asctime)s: %(levelname)s] " \
               "[%(module)s: %(lineno)d] %(message)s"
LFORMAT = "[%(asctime)s: %(levelname)s] %(message)s"
ACCEPTED_INPUT = set(["yes", "y"])


def status_study(args):
    """Check and print the status of an executing study."""
    # Force logging to Warning and above
    LOG_UTIL.configure(LFORMAT, log_lvl=3)

    directory_list = args.directory

    if directory_list:

        for path in directory_list:
            abs_path = os.path.abspath(path)

            status = Conductor.get_status(abs_path)
            status_layout = args.layout

            if status:
                try:
                    # Wasteful to not reuse this renderer for all paths?
                    status_renderer = status_renderer_factory.get_renderer(
                        status_layout, args.disable_theme, args.disable_pager)

                except ValueError:
                    print("Layout '{}' not implemented.".format(status_layout))
                    raise

                status_renderer.layout(status_data=status,
                                       study_title=abs_path,
                                       filter_dict=None)

                status_renderer.render()

            else:
                print(
                    "\nNo status to report -- the Maestro study in this path "
                    "either unexpectedly crashed or the path does not contain "
                    "a Maestro study.")

    else:
        print(
            "Path(s) or glob(s) did not resolve to a directory(ies) that "
            "exists.")
        return 1

    return 0


def cancel_study(args):
    """Flag a study to be cancelled."""
    # Force logging to Warning and above
    LOG_UTIL.configure(LFORMAT, log_lvl=3)

    directory_list = args.directory

    ret_code = 0
    to_cancel = []
    if directory_list:
        for directory in directory_list:
            abs_path = os.path.abspath(directory)
            if not os.path.isdir(abs_path):
                print(
                    f"Attempted to cancel '{abs_path}' "
                    "-- study directory not found.")
                ret_code = 1
            else:
                print(f"Study in '{abs_path}' to be cancelled.")
                to_cancel.append(abs_path)

        if to_cancel:
            ok_cancel = input("Are you sure? [y|[n]]: ")
            try:
                if ok_cancel in ACCEPTED_INPUT:
                    for directory in to_cancel:
                        Conductor.mark_cancelled(directory)
            except Exception as excpt:
                print(f"Error:\n{excpt}")
                print("Error in cancellation. Aborting.")
                return -1
        else:
            print("Cancellation aborted.")
    else:
        print("Path(s) or glob(s) did not resolve to a directory(ies).")
        ret_code = 1

    return ret_code


def load_parameter_generator(path, env, kwargs):
    """
    Import and load custom parameter Python files.

    :param path: Path to a Python file containing the function \
    'get_custom_generator'.
    :param env: A StudyEnvironment object containing custom information.
    :param kwargs: Dictionary containing keyword arguments for the function \
    'get_custom_generator'.
    :returns: A populated ParameterGenerator instance.
    """
    path = os.path.abspath(path)
    LOGGER.info("Loading custom parameter generator from '%s'", path)
    try:
        # Python 3.5
        import importlib.util
        LOGGER.debug("Using Python 3.5 importlib...")
        spec = importlib.util.spec_from_file_location("custom_gen", path)
        f = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(f)
        return f.get_custom_generator(env, **kwargs)
    except ImportError:
        try:
            # Python 3.3
            from importlib.machinery import SourceFileLoader
            LOGGER.debug("Using Python 3.4 SourceFileLoader...")
            f = SourceFileLoader("custom_gen", path).load_module()
            return f.get_custom_generator(env, **kwargs)
        except ImportError:
            # Python 2
            import imp
            LOGGER.debug("Using Python 2 imp library...")
            f = imp.load_source("custom_gen", path)
            return f.get_custom_generator(env, **kwargs)
    except Exception as e:
        LOGGER.exception(str(e))
        raise e


def run_study(args):
    """Run a Maestro study."""
    # Report log lvl
    LOGGER.info("INFO Logging Level -- Enabled")
    LOGGER.warning("WARNING Logging Level -- Enabled")
    LOGGER.critical("CRITICAL Logging Level -- Enabled")
    LOGGER.debug("DEBUG Logging Level -- Enabled")
    # Load the Specification
    try:
        spec = YAMLSpecification.load_specification(args.specification)
    except jsonschema.ValidationError as e:
        LOGGER.error(e.message)
        sys.exit(1)
    environment = spec.get_study_environment()
    steps = spec.get_study_steps()

    # Set up the output directory.
    out_dir = environment.remove("OUTPUT_PATH")
    if args.out:
        # If out is specified in the args, ignore OUTPUT_PATH.
        output_path = os.path.abspath(args.out)

        # If we are automatically launching, just set the input as yes.
        if os.path.exists(output_path):
            if args.autoyes:
                uinput = "y"
            elif args.autono:
                uinput = "n"
            else:
                uinput = six.moves.input(
                    "Output path already exists. Would you like to overwrite "
                    "it? [yn] ")

            if uinput.lower() in ACCEPTED_INPUT:
                print("Cleaning up existing out path...")
                shutil.rmtree(output_path)
            else:
                print("Opting to quit -- not cleaning up old out path.")
                sys.exit(0)

    else:
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
        output_path = make_safe_path(out_dir, *[out_name])
    environment.add(Variable("OUTPUT_PATH", output_path))

    # Set up file logging
    create_parentdir(os.path.join(output_path, "logs"))
    log_path = os.path.join(output_path, "logs", "{}.log".format(spec.name))
    LOG_UTIL.add_file_handler(log_path, LFORMAT, args.debug_lvl)

    # Check for pargs without the matching pgen
    if args.pargs and not args.pgen:
        msg = "Cannot use the 'pargs' parameter without specifying a 'pgen'!"
        LOGGER.exception(msg)
        raise ArgumentError(msg)

    # Addition of the $(SPECROOT) to the environment.
    spec_root = os.path.split(args.specification)[0]
    spec_root = Variable("SPECROOT", os.path.abspath(spec_root))
    environment.add(spec_root)

    # Handle loading a custom ParameterGenerator if specified.
    if args.pgen:
        # 'pgen_args' has a default of an empty list, which should translate
        # to an empty dictionary.
        kwargs = create_dictionary(args.pargs)
        # Copy the Python file used to generate parameters.
        shutil.copy(args.pgen, output_path)

        # Add keywords and environment from the spec to pgen args.
        kwargs["OUTPUT_PATH"] = output_path
        kwargs["SPECROOT"] = spec_root

        # Load the parameter generator.
        parameters = load_parameter_generator(args.pgen, environment, kwargs)
    else:
        parameters = spec.get_parameters()

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

    # Set up the study workspace and configure it for execution.
    study.setup_workspace()
    study.configure_study(
        throttle=args.throttle, submission_attempts=args.attempts,
        restart_limit=args.rlimit, use_tmp=args.usetmp, hash_ws=args.hashws,
        dry_run=args.dry)
    study.setup_environment()

    if args.dry:
        # If performing a dry run, drive sleep time down to generate scripts.
        sleeptime = 1
    else:
        # else, use args to decide sleeptime
        sleeptime = args.sleeptime

    batch = {"type": "local"}
    if spec.batch:
        batch = spec.batch
        if "type" not in batch:
            batch["type"] = "local"
    # Copy the spec to the output directory
    shutil.copy(args.specification, study.output_path)

    # Use the Conductor's classmethod to store the study.
    Conductor.store_study(study)
    Conductor.store_batch(study.output_path, batch)

    # If we are automatically launching, just set the input as yes.
    if args.autoyes or args.dry:
        uinput = "y"
    elif args.autono:
        uinput = "n"
    else:
        uinput = six.moves.input("Would you like to launch the study? [yn] ")

    if uinput.lower() in ACCEPTED_INPUT:
        if args.fg:
            # Launch in the foreground.
            LOGGER.info("Running Maestro Conductor in the foreground.")
            conductor = Conductor(study)
            conductor.initialize(batch, sleeptime)
            completion_status = conductor.monitor_study()
            conductor.cleanup()
            return completion_status.value
        else:
            # Launch manager with nohup
            log_path = make_safe_path(
                study.output_path,
                *["{}.txt".format(study.name)])

            cmd = ["nohup", "conductor",
                   "-t", str(sleeptime),
                   "-d", str(args.debug_lvl),
                   study.output_path,
                   ">", log_path, "2>&1"]
            LOGGER.debug(" ".join(cmd))
            start_process(" ".join(cmd))

            print("Study launched successfully.")
    else:
        print("Study launch aborted.")

    return 0


def setup_argparser():
    """Set up the program's argument parser."""
    parser = ArgumentParser(
        prog="maestro",
        description="The Maestro Workflow Conductor for specifying, launching"
        ", and managing general workflows.",
        formatter_class=RawTextHelpFormatter)
    # This call applies a default function to the main parser as described
    # here: https://stackoverflow.com/a/61680800
    parser.set_defaults(func=lambda args: parser.print_help())
    subparsers = parser.add_subparsers(dest='subparser')

    # subparser for a cancel subcommand
    cancel = subparsers.add_parser(
        'cancel',
        help="Cancel all running jobs.")
    cancel.add_argument(
        "directory", type=str, nargs="+",
        help="Directory containing a launched study.")
    cancel.set_defaults(func=cancel_study)

    # subparser for a run subcommand
    run = subparsers.add_parser('run',
                                help="Launch a study based on a specification")
    run.add_argument("-a", "--attempts", type=int, default=1,
                     help="Maximum number of submission attempts before a "
                     "step is marked as failed. [Default: %(default)d]")
    run.add_argument("-r", "--rlimit", type=int, default=1,
                     help="Maximum number of restarts allowed when steps. "
                     "specify a restart command (0 denotes no limit). "
                     "[Default: %(default)d]")
    run.add_argument("-t", "--throttle", type=int, default=0,
                     help="Maximum number of inflight jobs allowed to execute "
                     "simultaneously (0 denotes not throttling). "
                     "[Default: %(default)d]")
    run.add_argument("-s", "--sleeptime", type=int, default=60,
                     help="Amount of time (in seconds) for the manager to "
                     "wait between job status checks. [Default: %(default)d]")
    run.add_argument("--dry", action="store_true", default=False,
                     help="Generate the directory structure and scripts for a "
                     "study but do not launch it. [Default: %(default)s]")
    run.add_argument("-p", "--pgen", type=str,
                     help="Path to a Python code file containing a function "
                     "that returns a custom filled ParameterGenerator "
                     "instance.")
    run.add_argument("--pargs", type=str, action="append", default=[],
                     help="A string that represents a single argument to pass "
                     "a custom parameter generation function. Reuse '--parg' "
                     "to pass multiple arguments. [Use with '--pgen']")
    run.add_argument("-o", "--out", type=str,
                     help="Output path to place study in. [NOTE: overrides "
                     "OUTPUT_PATH in the specified specification]")
    run.add_argument("-fg", action="store_true", default=False,
                     help="Runs the backend conductor in the foreground "
                     "instead of using nohup. [Default: %(default)s]")
    run.add_argument("--hashws", action="store_true", default=False,
                     help="Enable hashing of subdirectories in parameterized "
                     "studies (NOTE: breaks commands that use parameter labels"
                     " to search directories). [Default: %(default)s]")

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
        "directory", type=str, nargs="+",
        help="Directory containing a launched study.")
    status.add_argument(
        "--layout", type=str, choices=status_renderer_factory.get_layouts(),
        default='flat',
        help="Alternate status table layouts. [Default: %(default)s]")
    status.add_argument(
        "--disable-theme", action="store_true", default=False,
        help="Turn off styling for the status layout. (If you want styling but it's not working, try modifying "
        "the MANPAGER or PAGER environment variables to be 'less -r'; i.e. export MANPAGER='less -r')"
    )
    status.add_argument(
        "--disable-pager", action="store_true", default=False,
        help="Turn off the pager functionality when viewing the status."
    )
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
    parser.add_argument(
        "-v", "--version", action="version", version='%(prog)s ' + __version__)

    return parser


def main():
    """
    Execute the main program's functionality.

    This function uses command line arguments to locate the study description.
    It makes use of the maestrowf core data structures as a high level class
    interface.
    """
    # Set up the necessary base data structures to begin study set up.
    parser = setup_argparser()
    args = parser.parse_args()

    # If we have requested to log stdout, set it up to be logged.
    if args.logstdout:
        if args.debug_lvl == 1:
            lformat = DEBUG_FORMAT
        else:
            lformat = LFORMAT
        LOG_UTIL.configure(lformat, args.debug_lvl)

    rc = args.func(args)
    sys.exit(rc)


if __name__ == "__main__":
    main()
