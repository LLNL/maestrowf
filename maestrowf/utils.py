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
import random
import coloredlogs
from filelock import SoftFileLock as FileLock
from jinja2 import Template
import logging
import os
import string
from subprocess import PIPE, Popen
from six.moves.urllib.request import urlopen
from six.moves.urllib.error import HTTPError, URLError
import time
import datetime
import pprint
from collections import defaultdict

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
    else:
        msg = \
            "Encountered an object of type '{}'. Passing." \
            .format(type(item))
        LOGGER.debug(msg)
        return item


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

def splitall(path):
    """
    Split path into a list of component directories.
    https://www.oreilly.com/library/view/python-cookbook/0596001673/ch04s16.html
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

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
    return next_index_and_path(path_pattern)[1]


def next_index_and_path(path_pattern):
    """
    Finds the next index number free path in an sequentially named list of files

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

    return b, path_pattern % b

def recursive_render(tpl, values):
    """
    Repeat rendering of jinja template until there are no changes.

    https://stackoverflow.com/questions/8862731/jinja-nested-rendering-on-variable-content
    """
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
            self, make_links_flag=False, hashws=False,
            link_template=None, output_name=None, output_path=None,
            spec_name=None,date_string=None,time_string=None,
            dir_float_format=['{:.2f}','{:.2e}'], pgen=None, globals={}):
        """
        Initialize a new Linker class instance.

        :param make_links_flag: Enable customizable, human-readable links to
            run directories.
        :param link_template: Jinja template for links to run directories.
        """
        self.make_links_flag = make_links_flag
        self.link_template = link_template
        self.output_name = output_name
        self.output_path = output_path
        self.spec_name=spec_name
        self.date_string=date_string
        self.time_string=time_string
        self.dir_float_format = dir_float_format
        self.pgen = pgen
        self.globals = globals
        self.study_index = 0
        self.combo_index = defaultdict(int)
        self._study_datetime = datetime.datetime.now()
        # if hashws:
        #     LOGGER.warning("'--make-links' option is not supported with '--hashws' option (hash workspace).")
        #     self.make_links_flag = False
        #     return
        if make_links_flag:
            self.validate_link_template(link_template)

    def validate_link_template(self, link_template):
        """ 
        Validate link template.
        The template must have enough information to generate a 
        unique path for each study and each combo in the study.
        """
        # @TODO: generalize to work if there are no combos.
        error = False
        error_text = ""
        study_index_index = link_template.find('{{study_index}}')

        study_index_index = link_template.find('{{study_index}}')
        output_name_index = link_template.find('{{output_name}}')
        study_time_index = link_template.find('{{study_time}}')
        study_date_index = link_template.find('{{study_date}}')
        date_index = link_template.find('{{date}}')
        if study_index_index == -1 and output_name_index == -1:
            if study_time_index == -1:
                error = True
            if study_date_index == -1 and date_index == -1:
                error = True
            if error:
                error_text += (
                   f"Template error: '{link_template}'\n"
                    "    does not include required 'study' substrings \n"                    
                    "    {{study_time}} and {{study_date}} or {{date}},\n"
                    "    or {{study_index}}, or {{output_name}}.\n")
        if self.pgen != None or self.globals != {}:
            max_study_index = max(study_index_index, output_name_index,
                study_time_index, study_date_index, date_index)
            combo_index_index = link_template.find('{{combo_index}}')
            combo_index = link_template.find('{{combo}}')
            min_key_index = float("inf")
            var_list = ["{{" + var + "}}" for var in self.globals.keys()]
            for key in self.globals.keys():
                key_index = link_template.find('{{' + key + '}}')
                if key_index < min_key_index:
                    min_key_index = key_index
            min_combo_list = ([var for var in [combo_index, combo_index_index, min_key_index]
                                   if var > -1])
            if min_combo_list:
                min_combo_index = min(min_combo_list)
            else:
                min_combo_index = -1
            if combo_index_index == -1 and combo_index == -1 and min_key_index == -1:
                error = True
                error_text += (
                    f"Template error: '{link_template}'\n"
                    f"    does not include required 'combo' substrings \n"                    
                        "    {{combo_index}}, or {{combo}},\n"
                    f"    or all global variables ({var_list})\n")
            if min_combo_index < max_study_index:
                error = True
                error_text += (
                    f"Template error: in '{link_template}'\n"
                    "    This code requires all combo substrings to be to the right\n"
                    "    of all study stubstrings.\n"
                    "    The position of the rightmost 'study' substrings \n"
                    "    ({{study_index}}, {{study_time}}, {{study_date}}, or {{date}})\n"
                    "    is to the right of the leftmost 'combo' substrings\n"
                    "    ({{combo}}, {{combo_index}}, or all global variables\n"
                    f"     ({var_list})).\n"
                    )  
        if link_template.count('{{study_index}}') > 1:
            error = True
            error_text += (
                f"Template error: in '{link_template}'\n"
                "    '{{study_index}}' can not be repeated.")
        if link_template.count('{{combo_index}}') > 1:
            error = True
            error_text += (
                f"Template error: in '{link_template}'\n"
                "    '{{combo_index}}' can not be repeated.")
        if error:
            print(error_text)
            raise ValueError(error_text)

    @staticmethod
    def format_float(num, format_list):
            """
            Return num as string using format_list.
            
            format_list, for example (['{:.2f}','{:.2e}']),
            contains "".format() style format strings for 
            numbers with small exponents and for numbers with
            large exponents.
            """
            if type(num) != float:
                return str(num)
            float_string = "{}".format(num)
            if float_string.find("e") > -1:
                formatted_string = format_list[1].format(num)
            else:
                formatted_string = format_list[0].format(num)
            return formatted_string
    

    def build_replacements(self, record):
        """ build replacements dictionary from StepRecord"""
        # {{study-name}} {{step-name}} {{study-index}} {{combo-index}}
        replacements = {}
        # output_name = self.output_name
        # study_time = output_name.split("-")[-1]
        replacements['study_time'] = self.time_string
        # study_date = output_name.split("_")[-1].replace(f"-{study_time}","")
        replacements['study_date'] = self.date_string
        # study_name = output_name.replace(f"_{study_date}-{study_time}","")
        replacements['study_name'] = self.spec_name
        replacements['link_template'] = self.link_template
        replacements['output_name'] = self.output_name
        replacements['output_path'] = self.output_path
        replacements['date'] = self._study_datetime.strftime('%Y-%m-%d')
        if type(self.study_index) == int:
            replacements["study_index"] = "{{study_index}}"
        else:
            replacements["study_index"] = self.study_index
        LOGGER.info(f"DEBUG step: {str(record.step)}")
        if record.step.combo != None and record._params:
            # long_combo = os.path.basename(record.workspace.value)
            long_combo = record.step._param_string
            if type(self.combo_index[long_combo]) == int:
                replacements["combo_index"] = "{{combo_index}}"
            else:
                replacements["combo_index"] = self.combo_index[long_combo]
            combo = long_combo
            replacements['long_combo'] = long_combo
            replacements['nickname'] = record.step.nickname
            step = record.name.replace("_" + combo,"")
            for param, name in zip(
                record.step.combo._params.values(),
                record.step.combo._labels.values()):
                combo = combo.replace(
                    name, 
                    name.replace(
                        str(param), 
                        self.format_float(param, self.dir_float_format))
                )
            replacements['step'] = step
            replacements['combo'] = combo
        else:
            replacements['step'] = record.name
            replacements['combo'] = "all_records"
            replacements['long_combo'] = "all_records"
            replacements['nickname'] = None
        if record.step.combo != None and record._params:
            for param, name in zip(
                record.step.combo._params.items(),
                record.step.combo._names.items()):
                key = name[1]
                value = param[1]
                if key not in replacements:
                    replacements[key] = value
        return replacements

    @staticmethod
    def split_directory(dir, split_string):
        """
        Split directory into three pieces
        The central piece will contain the 'split_string'
        """
        if dir.find(split_string) == -1:
            return (dir, "", "")
        dir_list = splitall(dir)
        left_dirs = []
        right_dirs = []
        found = False
        for dir in dir_list:
            if found:
                right_dirs.append(dir)
            else:
                if dir.find(split_string) == -1:
                    left_dirs.append(dir)
                else:
                    index_dir = dir
                    found = True
        return (
            os.path.join(*left_dirs), 
            index_dir, 
            os.path.join(*right_dirs))

    def new_index(self, dir, index_name):
        """
        Generate a new index.
        `index_name` is {{study-index}} or {{combo-index}}
        """
        if dir.find(index_name) == -1:
            return self.index_format % 0
        left_dirs, index_dir, right_dirs = (
            self.split_directory(dir, index_name))
        if "{" in left_dirs:
            raise ValueError(
                "ERROR: the following path should not have any jinja "
                f"variables: {left_dirs}")
        os.makedirs(left_dirs, exist_ok=True)
        return self.next_path_w_lock(os.path.join(left_dirs, index_dir), index_name)

    def next_path_w_lock(self, path_with_index, index_name):
        """
        Thread safe version of next_path. 
        Returns formatted index string.
        """
        pass
        success = False
        timeout = time.time() + self.mkdir_timeout
        lock_file = path_with_index.replace(index_name, "lock")
        template = path_with_index.replace(index_name, self.index_format)
        lock = FileLock(
            lock_file,
            timeout=2*self.mkdir_timeout)
        with lock:
            while not success and time.time() < timeout:
                try:
                    index, index_directory_string = next_index_and_path(template)
                    os.makedirs(index_directory_string)
                    success = True
                except OSError as e:
                    if e.args[1] == 'File exists':
                        time.sleep(random.uniform(
                            0.05*self.mkdir_timeout,
                            0.10*self.mkdir_timeout))
                    elif e.args[1] == 'Permission denied':
                        raise(ValueError(
                            "Could not create a unique directory "
                            "because of a "
                            "permissions error.\n\n"
                            f"Attempted path: {index_directory_string}"
                            ))
                    else:
                        raise(ValueError(e))
        return self.index_format % index

    def link(self, record):
        """Create link for StepRecord"""
        # @TODO: test cases: index in front, middle, end, no index, two indexes
        #        with and without hash
        if not self.make_links_flag:
            return
        replacements = self.build_replacements(record)
        link_path = recursive_render(self.link_template, replacements)
        if type(self.study_index) == int:
            new_index = self.new_index(link_path, "{{study_index}}")
            self.study_index = new_index
            replacements = self.build_replacements(record)
            link_path = recursive_render(self.link_template, replacements)
        if type(self.combo_index[replacements['long_combo']]) == int:
            new_index = self.new_index(link_path, "{{combo_index}}")           
            self.combo_index[replacements['long_combo']] = new_index    
            replacements = self.build_replacements(record)
        link_path = recursive_render(self.link_template, replacements)
        LOGGER.info(f"DEBUG: \n{pprint.pformat(replacements)}")
        try:
            # make full path; then make link
            os.makedirs(link_path)
            os.rmdir(link_path)
            link_target = record.workspace.value
            if replacements['nickname']:
                link_target.replace(replacements['long_combo'], replacements['nickname'])
            os.symlink(link_target, link_path)
        except OSError as e:
            if e.args[1] == 'File exists':
                raise(ValueError(
                    "Could not create a unique directory.\n\n" +
                    "Attempted path: " + link_path + "\n" +
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
