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
import logging
import os
import string
from subprocess import PIPE, Popen
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError, URLError
import time

LOGGER = logging.getLogger(__name__)


def get_duration(time_delta):
    """
    Covert durations to HH:MM:SS format.

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
    Utility function that recursively creates parent directories.

    :param path: Path to a directory to be created.
    """
    if not os.path.exists(path):
        LOGGER.info("Directory does not exist. Creating directories to %s",
                    path)
        path = os.path.expanduser(path)
        os.makedirs(path)


def apply_function(item, func):
    """
    Utility function for applying a wider range of functions to items.

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
    :params *args: Path components to join into a path.
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
    Starts a new process using a specified command.

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
