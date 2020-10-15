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

"""A collection of more general utility functions."""

from collections import OrderedDict
import coloredlogs
import logging
import os
import string
from subprocess import PIPE, Popen
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError, URLError
import time
import datetime
from jinja2 import Template
import re
from filelock import SoftFileLock as FileLock
from filelock import Timeout
import random

LOGGER = logging.getLogger(__name__)


def get_duration(time_delta):
    """
    Convert durations to HH:MM:SS format.

    :params time_delta: A time difference in datatime format.
    :returns: A formatted string in HH:MM:SS
    """
    duration = time_delta.total_seconds()
    days = int(duration / 86400)
    hours = int((duration % 86400) / 3600)
    minutes = int((duration % 86400 % 3600) / 60)
    seconds = int((duration % 86400 % 3600) % 60)

    return "{:d}d:{:02d}h:{:02d}m:{:02d}s" \
           .format(days, hours, minutes, seconds)


def round_datetime_seconds(input_datetime):
    """
    Round datetime to the nearest whole second.

    Solution referenced from: https://stackoverflow.com/questions/47792242/
    rounding-time-off-to-the-nearest-second-python.

    :params input_datetime: A datetime in datatime format.
    :returns: ``input_datetime`` rounded to the nearest whole second
    """
    new_datetime = input_datetime

    if new_datetime.microsecond >= 500000:
        new_datetime = new_datetime + datetime.timedelta(seconds=1)

    return new_datetime.replace(microsecond=0)


def generate_filename(path, append_time=True):
    """
    Generate a non-conflicting file name.

    :param path: Path to file.
    :param append_time: Setting to append a timestamp.
    """
    LOGGER.debug("Parameter path = %s", path)
    path = os.path.expanduser(path)
    root, ext = os.path.splitext(path)
    parent = os.path.dirname(root)
    fname = os.path.basename(root)

    LOGGER.debug("Expanded path = %s", path)
    LOGGER.debug("Root, Extension = (%s, %s)", root, ext)
    LOGGER.debug("Parent directory = %s", parent)
    LOGGER.debug("Filename = %s", fname)

    index = 0
    timestamp = ''
    if append_time:
        timestamp = '_{0}'.format(time.strftime("%Y%m%d-%H%M%S"))

    candidate = "{0}{1}{2}".format(fname, timestamp, ext)
    ls_files = set(os.listdir(parent))

    while candidate in ls_files:
        candidate = "{0}_{1:05d}{2}".format(root, index, ext)
        index += 1

    return os.path.join(parent, candidate)


def create_parentdir(path):
    """
    Recursively create parent directories.

    :param path: Path to a directory to be created.
    """
    if not os.path.exists(path):
        LOGGER.info("Directory does not exist. Creating directories to %s",
                    path)
        path = os.path.expanduser(path)
        os.makedirs(path)


def apply_function(item, func):
    """
    Apply a function to items depending on type.

    :param item: A Python primitive to apply a function to.
    :param func: Function that returns takes item as a parameter and returns
        item modified in some way.
    """
    if not item:
        return item
    elif isinstance(item, str):
        return func(item)
    elif isinstance(item, list):
        return [apply_function(x, func) for x in item]
    elif isinstance(item, dict):
        return {
            key: apply_function(value, func) for key, value in item.items()}
    elif isinstance(item, int):
        return item
    else:
        msg = "Encountered an object of type '{}'. Expected a str, list, int" \
              ", or dict.".format(type(item))
        LOGGER.error(msg)
        raise ValueError(msg)


def csvtable_to_dict(fstream):
    """
    Convert a csv file stream into an in memory dictionary.

    :param fstream: An open file stream to a csv table (with header)
    :returns: A dictionary with a key for each column header and a list of
        column values for each key.
    """
    # Read in the lines from the file stream.
    lines = fstream.readlines()
    # There are two pieces of information we need for the headers:
    # 1. The actual header titles.
    # 2. A map of index to header title
    _ = lines.pop(0).strip("\n").split(",")
    # Retain the order of the columns as they're added.
    table = OrderedDict()
    # A map of row index to the appropriate header.
    indices = {}
    i = 0
    # For each item in the header, mark its index and initialize its column.
    for item in _:
        indices[i] = item
        table[item] = []
        i += 1

    # Walk each line of the table, mapping the columns in the row to their key.
    for line in lines:
        # Split the csv row
        _ = line.split(",")
        # Walk each column and map it.
        for i in range(len(_)):
            table[indices[i]].append(_[i].strip("\n"))

    # Return the completed table
    return table


def make_safe_path(base_path, *args):
    """
    Construct a subpath that is path safe.

    :params base_path: The base path to append args to.
    :params args: Path components to join into a path.
    :returns: A joined subpath with invalid characters stripped.
    """
    valid = "-_.() {}{}".format(string.ascii_letters, string.digits)
    path = [base_path]
    for arg in args:
        arg = "".join(c for c in arg if c in valid)
        arg = arg.replace(" ", "_")
        path.append(arg)
    return os.path.join(*path)


def start_process(cmd, cwd=None, env=None, shell=True):
    """
    Start a new process using a specified command.

    :param cmd: A string or a list representing the command to be run.
    :param cwd: Current working path that the process will be started in.
    :param env: A dictionary containing the environment the process will use.
    :param shell: Boolean that determines if the process will run a shell.
    """
    if isinstance(cmd, list):
        shell = False

    # Define kwargs for the upcoming Popen call.
    kwargs = {
        "shell":                shell,
        "universal_newlines":   True,
        "stdout":               PIPE,
        "stderr":               PIPE,
    }

    # Individually check if cwd and env are set -- this prevents us from
    # adding parameters to the command that are only set to defaults. It
    # also insulates us from potential default value changes in the future.
    if cwd is not None:
        kwargs["cwd"] = cwd

    if env is not None:
        kwargs["env"] = env

    return Popen(cmd, **kwargs)


def ping_url(url):
    """
    Load a webpage to test that it is accessible.

    :param url: URL string to be loaded.
    """
    try:
        response = urlopen(url)
    except HTTPError as e:
        LOGGER.error("Error fulfilling HTTP request. (%s)", e.code)
        raise e
    except URLError as e:
        LOGGER.error(
            "Check specified URL (%s) and that you are connected to the "
            "internet. (%s)", url, e.code)
        raise e
    else:
        response.read()
        return


def create_dictionary(list_keyvalues, token=":"):
    """
    Create a dictionary from a list of key-value pairs.

    :param list_keyvalues: List of token separates key-values.
    :param token: The token to split each key-value by.
    :returns: A dictionary containing the key-value pairings in list_keyvalues.
    """
    _dict = {}
    for item in list_keyvalues:
        try:
            key, value = [i.strip() for i in item.split(token, 1)]
            _dict[key] = value
        except ValueError:
            msg = "'{}' is not capable of being split by the token '{}'. " \
                  "Verify that all other parameters are formatted properly." \
                  .format(item, token)
            LOGGER.exception(msg)
            raise ValueError(msg)

    return _dict

def next_path(path_pattern):
    """
    Finds the next free path in an sequentially named list of files

    e.g. path_pattern = 'file-%s.txt':

    file-1.txt
    file-2.txt
    file-3.txt

    Runs in log(n) time where n is the number of existing files in sequence
    https://stackoverflow.com/questions/17984809/how-do-i-create-a-incrementing-filename-in-python
    """
    i = 1

    # First do an exponential search
    while os.path.exists(path_pattern % i):
        i = i * 2

    # Result lies somewhere in the interval (i/2..i]
    # We call this interval (a..b] and narrow it down until a + 1 = b
    a, b = (i // 2, i)
    while a + 1 < b:
        c = (a + b) // 2  # interval midpoint
        a, b = (c, b) if os.path.exists(path_pattern % c) else (a, c)

    return path_pattern % b

def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

def recursive_render(tpl, values):
    #https://stackoverflow.com/questions/8862731/jinja-nested-rendering-on-variable-content
    prev = tpl
    while True:
        curr = Template(prev).render(values)
        if curr != prev:
            prev = curr
        else:
            return curr

class Linker:
    """Utility class to make links."""
    index_format = '%04d'
    mkdir_timeout = 5  # seconds
    maestro_index_file = 'maestro_index_file'

    def __init__(
        self, make_links_flag=False, link_directory=None, link_template=None,
        output_name=None, output_root=None):
        """
        Initialize a new Linker class instance.

        :param make_links_flag: Enable customizable, human-readable links to
            run directories.
        :param link_directory: Jinja template for path where links to
            run directories are made.
        :param link_template: Jinja template for links to run directories.
        """
        self.make_links_flag = make_links_flag
        self.link_directory = link_directory
        self.link_template = link_template
        self.output_name = output_name
        self.output_root = output_root

    def split_indexed_directory(self, template_string):
        """
        Returns a tuple of a indexed_directory prefix, suffix & template

        Example `link_directory_template`: {{output_path_root}}/links/{{date}}/
            run-{{INDEX}}/{{instance}}/{{step}}

        Example `indexed_directory_prefix`: studies/links/2020_07_30
        Example `indexed_directory_suffix`: bar.1.foo.1.foobar.1/run-codepy-baseline/
        Example `indexed_directory_template`: run-{{INDEX}}

        :param link_directory_template: a one line jinja directory path template
        :param defs: a dictionary containing replacement definitions for
            ``link_directory_template``

        :returns: a tuple containing the indexed_directory prefix, suffix
            & template
        """
        # @TODO: test cases: index in front, middle, end, no index, two indexes
        # @TODO: other error checking on template_string?
        dir_list = splitall(template_string)
        indexed_directory_prefix = []
        indexed_directory_template = ""
        indexed_directory_suffix = []  
        while not re.match(r".*{{INDEX}}.*", dir_list[0]):
            indexed_directory_prefix.append(dir_list.pop(0))
        if dir_list:
            indexed_directory_template = dir_list.pop(0)
        if dir_list:
            while dir_list and not re.match(r".*{{INDEX}}.*", dir_list[0]):
                indexed_directory_suffix.append(dir_list.pop(0)) 
            if dir_list:   
                raise(ValueError(
                    "at most one '{{INDEX}}' can be in link path template string")) 
        return(indexed_directory_prefix, indexed_directory_suffix,
            indexed_directory_template)

    def link(self, record):
        # @TODO: test cases: index in front, middle, end, no index, two indexes
        #        with and without hash
        if not self.make_links_flag:
            return

        # build replacements dictionary
        replacements = {}
        # t = Template(self.link_directory)
        # replacements["link_directory"] = t.render(replacements)
        replacements['output_root'] = self.output_root
        replacements['date'] = time.strftime('%Y-%m-%d')
        (replacements['indexed_directory_prefix'],
            replacements['indexed_directory_suffix'],
            replacements['indexed_directory_template']) = (
            self.split_indexed_directory(self.link_template))
        LOGGER.info(f"CRKx record.step_label: {record.step_label}")
        LOGGER.info(f"CRKx record.name: {record.name}")
        if record.step_label:
            replacements['step'] = record.step_label
            replacements['instance'] = (
                record.name.replace(record.step_label + '_', ''))
        else:
            replacements['step'] = record.name
            replacements['instance'] = "all_records"
        replacements['link_directory'] = (
            recursive_render(
                self.link_directory, replacements))
        replacements['indexed_directory_prefix'] = [
            recursive_render(template_string, replacements)
            for template_string in replacements['indexed_directory_prefix']]
        replacements['indexed_directory_suffix'] = [
            recursive_render(template_string, replacements)
            for template_string in replacements['indexed_directory_suffix']]
        LOGGER.info(f"CRK suffix (1): {replacements['indexed_directory_suffix']}")

        # make link directories
        if len(replacements['indexed_directory_prefix']) == 0:
            raise(ValueError(
                "link_directory (" + self.link_directory + ")" +
                "and link_template (" + self.link_template + ")" +
                "do not result in a valid path for links."))

        # len(replacements['indexed_directory_prefix']) must be 1
        # because of error check in split_indexed_directory
        directory_prefix_path = os.path.join(
            *replacements['indexed_directory_prefix'])
        if replacements['indexed_directory_template']:
            maestro_index_file_path = (
                os.path.join(
                    self.output_root,
                    self.output_name, 
                    self.maestro_index_file))
            if os.path.exists(maestro_index_file_path):
                with open(maestro_index_file_path, "r") as f:
                    index_directory_string = f.readlines()[0].strip(" \n")
                    LOGGER.info(
                        f"CRK index_directory_string (from disk): "
                        f"{index_directory_string}")
            else:
                index_directory_template_string = (
                    replacements['indexed_directory_template'].replace(
                        '{{INDEX}}', self.index_format))
                success = False
                timeout = time.time() + self.mkdir_timeout
                LOGGER.info(f"CRK maestro_index_file_path: {maestro_index_file_path}")
                lock = FileLock(
                    maestro_index_file_path + ".lock", 
                    timeout=2*self.mkdir_timeout)
                with lock:
                    while not success and time.time() < timeout:
                        try:
                            index_directory_string = next_path(os.path.join(
                                directory_prefix_path,
                                index_directory_template_string
                                ))
                            os.makedirs(index_directory_string)
                            with open(maestro_index_file_path, "w") as f:
                                f.write(index_directory_string + "\n")
                            LOGGER.info(
                                f"CRK index_directory_string (from scratch): "
                                f"{index_directory_string}")
                            success = True
                        except OSError as e:
                            if e.args[1] == 'File exists':
                                time.sleep(random.uniform(
                                    0.05*self.mkdir_timeout,
                                    0.10*self.mkdir_timeout))
                            elif e.args[1] == 'Permission denied':
                                raise(ValueError(
                                    "Could not create a unique directory because of a " +
                                    "permissions error.\n\n" +
                                    "Attempted path: " + path + "\n" +
                                    "Template string: " + self.link_template 
                                    ))
                            else:
                                raise(ValueError(e))
            LOGGER.info(
                f"CRK suffix (2): "
                f">>{replacements['indexed_directory_suffix']}<<")
            LOGGER.info(
                f"CRK index_directory_string (2): "
                f">>{index_directory_string}<<")
            path = os.path.join(index_directory_string, 
                *replacements['indexed_directory_suffix'])
            LOGGER.info(f"CRK make_links_path: >>{path}<<")
        else:
            path = directory_prefix_path
        LOGGER.info(f"CRKx suffix (3): {replacements['indexed_directory_suffix']}")
        LOGGER.info(f"CRK make_links_path: {path}")
        try:
            # make full path; then make link
            os.makedirs(path)
            os.rmdir(path)
            os.symlink(record.workspace.value, path)
        except OSError as e:
            if e.args[1] == 'File exists':
                raise(ValueError(
                    "Could not create a unique directory.\n\n" +
                    "Attempted path: " + path + "\n" +
                    "Template string: " + self.link_template)) 
            elif e.args[1] == 'Permission denied':
                raise(ValueError(
                    "Could not create a unique directory because of a " +
                    "permissions error.\n\n" +
                    "Attempted path: " + path + "\n" +
                    "Template string: " + self.link_template 
                    ))
            else:
                raise(ValueError)


        LOGGER.info(f"CRK make_links_flag (link): {self.make_links_flag}")
        LOGGER.info(f"CRK PATH: {path}")
        LOGGER.info(f"CRK output_root (link): {self.output_root}")
        LOGGER.info(f"CRK link_directory (template): {self.link_directory}")
        LOGGER.info(f"CRK link_template (template): {self.link_template}")
        LOGGER.info(f"CRK link_directory (full): {replacements['link_directory']}")
        # LOGGER.info(f"CRK link_path (full): {t.render(replacements)}")
        LOGGER.info("CRK Creating directory: " + record.workspace.value)
        LOGGER.info("CRK Step label: " + record.step_label)
        LOGGER.info("CRK Step name: " + record.name)
        LOGGER.info(
            f"CRK indexed_directory_prefix: "
            f"{os.path.join(*replacements['indexed_directory_prefix'])}")
        # LOGGER.info(f"CRK indexed_directory_template: {replacements["indexed_directory_suffix"]}" )
        # LOGGER.info(f"CRK indexed_directory_suffix: {indexed_directory_suffix}" )

class LoggerUtility:
    """Utility class for setting up logging consistently."""

    def __init__(self, logger):
        """
        Initialize a new LoggerUtility class instance.

        :param logger: An instance of a logger to configure.
        """
        self._logger = logger

    def configure(self, log_format, log_lvl=2, colors=True):
        """
        Configures the general logging facility.

        :param log_format: String containing the desired logging format.
        :param log_lvl: Integer level (1-5) to set the logger to.
        """
        logging.basicConfig(level=self.map_level(log_lvl), format=log_format)
        if colors:
            coloredlogs.install(level=self.map_level(log_lvl),
                                logger=self._logger, fmt=log_format)

    def add_stream_handler(self, log_format, log_lvl=2):
        """
        Add a stream handler to logging.

        :param log_format: String containing the desired logging format.
        :param log_lvl: Integer level (1-5) to set the logger to.
        """
        # Create the FileHandler and add it to the logger.
        sh = logging.StreamHandler()
        sh.setLevel(self.map_level(log_lvl))
        sh.setFormatter(logging.Formatter(log_format))
        self._logger.addHandler(sh)

    def add_file_handler(self, log_path, log_format, log_lvl=2):
        """
        Add a file handler to logging.

        :param log_path: String containing the file path to store logging.
        :param log_format: String containing the desired logging format.
        :param log_lvl: Integer level (1-5) to set the logger to.
        """
        # Create the FileHandler and add it to the logger.
        formatter = logging.Formatter(log_format)

        fh = logging.FileHandler(log_path)
        fh.setLevel(self.map_level(log_lvl))
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)

    @staticmethod
    def map_level(log_lvl):
        """
        Map level 1-5 to their respective logging enumerations.

        :param log_lvl: Integer level (1-5) representing logging verbosity.
        """
        if log_lvl == 1:
            return logging.DEBUG
        elif log_lvl == 2:
            return logging.INFO
        elif log_lvl == 3:
            return logging.WARNING
        elif log_lvl == 4:
            return logging.ERROR
        else:
            return logging.CRITICAL
