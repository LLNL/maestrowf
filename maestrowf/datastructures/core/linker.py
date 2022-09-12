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

"""Utility class to make links."""

import random
import pprint
import datetime
import logging
import os
import time
from collections import defaultdict

from filelock import SoftFileLock as FileLock

from maestrowf.utils import splitall, next_index_and_path, recursive_render

LOGGER = logging.getLogger(__name__)


class Linker:
    """Utility class to make links."""
    index_format = '%04d'
    mkdir_timeout = 5  # seconds

    def __init__(
            self, make_links_flag=False, hashws=False,
            link_template=None, output_name=None, output_path=None,
            spec_name=None, date_string=None, time_string=None,
            dir_float_format=['{:.2f}', '{:.2e}'], pgen=None, globals={}):
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
        self.spec_name = spec_name
        self.date_string = date_string
        self.time_string = time_string
        self.dir_float_format = dir_float_format
        self.pgen = pgen
        self.globals = globals
        self.study_index = 0
        self.combo_index = defaultdict(int)
        self._study_datetime = datetime.datetime.now()
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
        output_name_index = link_template.find('{{output_name}}')
        study_time_index = link_template.find('{{study_time}}')
        study_date_index = link_template.find('{{study_date}}')
        date_index = link_template.find('{{date}}')
        max_study_index = max(study_index_index, output_name_index,
                                study_time_index, study_date_index,
                                date_index)
        if study_index_index == -1 and output_name_index == -1:
            if study_time_index == -1:
                error = True
            if study_date_index == -1 and date_index == -1:
                error = True
            if error:
                error_text += (
                    f"Template error: '{link_template}'\n"
                    f"    does not include required 'study' variables \n"
                    "    {{study_time}} and {{study_date}} or {{date}},\n"
                    "    or {{study_index}}, or {{output_name}}.\n")
        step_index = link_template.find('{{step}}')
        if step_index == -1:
            error = True
            error_text += (
                f"Template error: '{link_template}'\n"
                "    does not include required {{step}} variable.\n")
        if self.pgen is not None or self.globals != {}:
            combo_index_index = link_template.find('{{combo_index}}')
            combo_index = link_template.find('{{combo}}')
            min_key_index = float("inf")
            var_list = ["{{" + var + "}}" for var in self.globals.keys()]
            for key in self.globals.keys():
                key_index = link_template.find('{{' + key + '}}')
                if key_index < min_key_index:
                    min_key_index = key_index
            min_combo_list = (
                [var for var in [combo_index, combo_index_index, min_key_index]
                 if var > -1])
            if min_combo_list:
                min_combo_index = min(min_combo_list)
            else:
                min_combo_index = -1
            if (combo_index_index == -1
                    and combo_index == -1
                    and min_key_index == -1):
                error = True
                error_text += (
                    f"Template error: '{link_template}'\n"
                    f"    does not include required 'combo' variables \n"
                    f"    {{combo_index}}, or {{combo}},\n"
                    f"    or all global variables ({var_list})\n")
            if min_combo_index < max_study_index:
                error = True
                error_text += (
                    f"Template error: in '{link_template}'\n"
                    + "    This code requires all combo variables to be to the right\n"  # noqa: E501
                    "    of all study variables.\n"
                    "    The position of the rightmost 'study' variables \n"
                    "    ({{study_index}}, {{study_time}}, {{study_date}}, or {{date}})\n"  # noqa: E501
                    "    is to the right of the leftmost 'combo' variables\n"
                    "    ({{combo}}, {{combo_index}}, or all global variables\n"  # noqa: E501
                    f"     ({var_list})).\n"
                    )
            if link_template.count('{{combo_index}}') > 1:
                error = True
                error_text += (
                    f"Template error: in '{link_template}'\n"
                    "    '{{combo_index}}' can not be repeated.")
        if step_index < max_study_index:
            error = True
            error_text += (
                f"Template error: in '{link_template}'\n"
                "    This code requires the {{step}} variable to be to the right\n"  # noqa: E501
                "    of all study stubstrings.\n"
                "    The position of the rightmost 'study' variables \n"
                "    ({{study_index}}, {{study_time}}, {{study_date}}, or {{date}})\n"  # noqa: E501
                "    is to the right of the {{step}} variable.\n")
            error = True
        if link_template.count('{{study_index}}') > 1:
            error = True
            error_text += (
                f"Template error: in '{link_template}'\n"
                "    '{{study_index}}' can not be repeated.")
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
        replacements['study_time'] = self.time_string
        replacements['study_date'] = self.date_string
        replacements['study_name'] = self.spec_name
        replacements['link_template'] = self.link_template
        replacements['output_name'] = self.output_name
        replacements['output_path'] = self.output_path
        replacements['date'] = self._study_datetime.strftime('%Y-%m-%d')
        if type(self.study_index) == int:
            replacements["study_index"] = "{{study_index}}"
        else:
            replacements["study_index"] = self.study_index
        replacements['step'] = record.step.step_name
        if record.step.combo is not None and record._params:
            # long_combo = os.path.basename(record.workspace.value)
            long_combo = record.step._param_string
            if type(self.combo_index[long_combo]) == int:
                replacements["combo_index"] = "{{combo_index}}"
            else:
                replacements["combo_index"] = self.combo_index[long_combo]
            combo = long_combo
            replacements['long_combo'] = long_combo
            replacements['nickname'] = record.step.nickname

            for param, name in zip(
                record.step.combo._params.values(),
                record.step.combo._labels.values()):  # noqa: E125
                    combo = combo.replace(  # noqa: E117
                        name,
                        name.replace(
                            str(param),
                            self.format_float(param, self.dir_float_format))
                    )
            # LOGGER.info(f"DEBUG step: {step}")
            # LOGGER.info(f"DEBUG record.name: {record.name}")

            # replacements['step'] = step
            replacements['combo'] = combo
        else:
            # replacements['step'] = record.name
            replacements['combo'] = "all_records"
            replacements['long_combo'] = "all_records"
            replacements['nickname'] = None
        if record.step.combo is not None and record._params:
            print(f"debug combo: {combo}")
            for param, name in zip(
                record.step.combo._params.items(),
                record.step.combo._names.items()):
                print("param/name debug:", param, name)
                key = name[1]
                value = param[1]
                if (key in replacements
                    and self.link_template.find("{{" + key + "}}") > -1):
                        error_text = (
                            f"user key/value: {key}/{value} conflicts with "
                            f"maestro link template key/value: "
                            f"{key}/{replacements[key]}.")
                        LOGGER.error(error_text)
                        raise ValueError(error_text)
                replacements[key] = (
                    self.format_float(value, self.dir_float_format))
        # print(replacements['step'], "==?", replacements['step2'])
        # assert replacements['step'] == replacements['step2']
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
        return self.next_path_w_lock(
            os.path.join(left_dirs, index_dir), index_name)

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
                    index, index_directory_string = (
                        next_index_and_path(template))
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
                link_target.replace(
                    replacements['long_combo'],
                    replacements['nickname'])
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
                    "Attempted path: " + link_path + "\n" +
                    "Template string: " + self.link_template
                    ))
            else:
                raise(ValueError)
