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

"""
The core module contains all core abstracts and classes.

All core abstracts and implementations for core concept classes (Study,
Environment, Parameter generation, etc.). This module also includes interface
abstracts, base class abstracts, and general utilities.
"""
from abc import ABCMeta, abstractmethod
import inspect
from io import StringIO

import logging
import sys

try:
    from importlib.metadata import version
except ImportError as imp_err:
    # Remove this try/except upon deprecation of python 3.7
    from importlib_metadata import version

from rich import box
from rich.console import Console
from rich.table import Table
from rich.theme import Theme

import six

import tabulate

try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """Null logging handler for Python 3+."""

        def emit(self, record):
            """Override so that logging outputs nothing."""
            pass

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(NullHandler())

__version__ = version(__package__)


@six.add_metaclass(ABCMeta)
class BaseStatusRenderer:
    def __init__(self, *args, **kwargs):
        self._status_data = {}
        self._filters = {}
        self._study_title = ''
        self._theme_dict = {}

        self.disable_theme = kwargs.pop("disable_theme", False)
        self.disable_pager = kwargs.pop("disable_pager", False)

    @abstractmethod
    def layout(self, status_data, study_title=None, data_filters=None):
        """Setup concrete status layout

        Lays out the table data in a formatted string, storing it
        in renderer's `_status_table` attribute.

        Args:
            status_data (dict): study status dict, one column per key
            study_title (str): optional title of this study
            filter_dict (dict): optional data filter (not yet implemented)
        """
        pass

    def render(self, theme=None):
        """Do the actual printing"""
        # Apply any theme customization
        if theme:
            for key, value in theme.items():
                self._theme_dict[key] = value

        # If we're disabling the theme, we need to set all themes in the theme dict to none
        if self.disable_theme:
            for key in self._theme_dict.keys():
                self._theme_dict[key] = 'none'

        # Get the rich Console
        status_theme = Theme(self._theme_dict)
        _printer = Console(theme=status_theme)

        # Display the status table
        if self.disable_pager:
            _printer.print(self._status_table)
        else:
            with _printer.pager(styles=(not self.disable_theme)):
                _printer.print(self._status_table)


class LegacyStatusRenderer(BaseStatusRenderer):
    """Legacy tabulate based flat table layout"""

    layout_type = "legacy"      # Defines name in factory/cli

    def __init__(self, *args, **kwargs):
        super(LegacyStatusRenderer, self).__init__(*args, **kwargs)

    def layout(self, status_data, study_title=None, filter_dict=None):
        """Setup concrete status layout

        Lays out the table data in a formatted string, storing it
        in renderer's `_status_table` attribute.

        Args:
            status_data (dict): study status dict, one column per key
            study_title (str): optional title of this study
            filter_dict (dict): optional data filter (not yet implemented)
        """

        # Ensure status data is of type dict and isn't empty
        if isinstance(status_data, dict) and status_data:
            # Exclude the parameter column
            self._status_data = {key: value
                                 for key, value in status_data.items()
                                 if key != "Params"}
        else:
            raise ValueError("Status data required to layout a table")

        # Get the data, and compute header format length
        table_str = tabulate.tabulate(self._status_data, headers="keys")
        header_chars = max([len(line) for line in table_str.split("\n")])
        header_format = "".ljust(header_chars, "=")

        self._status_table = ""
        self._status_table += header_format + "\n"
        self._status_table += study_title + "\n"
        self._status_table += header_format + "\n"

        self._status_table += table_str + "\n"

        self._status_table += header_format + "\n"

    def render(self, theme=None):
        """Do the actual printing"""
        print(self._status_table)

    def render_to_str(self, theme=None, width=200):
        """Capture output to string"""

        return self._status_table


class FlatStatusRenderer(BaseStatusRenderer):
    """Flat, simple table layout"""

    layout_type = "flat"        # Defines name in factory/cli

    def __init__(self, *args, **kwargs):
        super(FlatStatusRenderer, self).__init__(*args, **kwargs)

        # Setup default theme
        self._theme_dict = {
            "State": "bold red",
            "Step Name": "bold",
            "Workspace": "blue",
            "Job ID": "yellow",
            "row_style": "none",
            "row_style_dim": "dim",
            "col_style_1": "",
            "col_style_2": "blue",
            "bgcolor": "grey7",
            "color": ""
        }

    def layout(self, status_data, study_title=None, filter_dict=None):
        """Setup concrete status layout

        Lays out the table data in a formatted string, storing it
        in renderer's `_status_table` attribute.

        Args:
            status_data (dict): study status dict, one column per key
            study_title (str): optional title of this study
            filter_dict (dict): optional data filter (not yet implemented)
        """

        # Ensure status data is of type dict and isn't empty
        if isinstance(status_data, dict) and status_data:
            self._status_data = status_data
        else:
            raise ValueError("Status data required to layout a table")

        """Construct the Rich Table object"""

        self._status_table = Table()
        if study_title:
            self._status_table.title = "Study: {}".format(study_title)

        # Apply any filters: TODO

        cols = list(self._status_data.keys())

        # Some temporary simple filters to exclude params col in this layout
        col_filters = ['Params']

        cols = [col for col in cols if col not in col_filters]

        # Setup the column styles
        for nominal_col_num, col in enumerate(cols):

            if col in list(self._theme_dict.keys()):
                col_style = col
            else:
                if nominal_col_num % 2 == 0:
                    col_style = 'col_style_1'
                else:
                    col_style = 'col_style_2'

            self._status_table.add_column(col,
                                          style=col_style,
                                          overflow="fold")

        num_rows = len(self._status_data[cols[0]])

        # Alternate dim rows to differentiate them better
        for row in range(num_rows):
            if row % 2 == 0:
                row_style = 'dim'
            else:
                row_style = 'none'

            self._status_table.add_row(
                *['{}'.format(self._status_data[key][row])
                  for key in cols],
                style=row_style
            )

    def render_to_str(self, theme=None, width=200):
        """Capture output to string"""

        # Apply any theme customization
        if theme:
            for key, value in theme.items():
                self._theme_dict[key] = value

        status_theme = Theme(self._theme_dict)

        _printer = Console(theme=status_theme,
                           file=StringIO(),
                           width=width)
        _printer.print(self._status_table)

        return _printer.file.getvalue()


class NarrowStatusRenderer(BaseStatusRenderer):
    """Narrow terminal layout with parameter info"""

    layout_type = "narrow"      # Defines name in factory/cli

    def __init__(self, *args, **kwargs):
        super(NarrowStatusRenderer, self).__init__(*args, **kwargs)

        # Setup default theme
        self._theme_dict = {
            "State": "bold red",
            "Step Name": "bold",
            "Workspace": "blue",
            "row_style": "",
            "row_style_dim": "dim",
            "background": "grey7"
        }

    def layout(self, status_data, study_title=None, filter_dict=None):
        """Setup concrete status layout

        Lays out the table data in a formatted string, storing it
        in renderer's `_status_table` attribute.

        Args:
            status_data (dict): study status dict, one column per key
            study_title (str): optional title of this study
            filter_dict (dict): optional data filter (not yet implemented)
        """

        # Ensure status data is of type dict and is not empty
        if isinstance(status_data, dict) and status_data:
            self._status_data = status_data
        else:
            raise ValueError("Status data required to layout a table")

        self._status_table = Table()
        if study_title:
            self._status_table.title = "Study: {}".format(study_title)

        # Apply any filters: TODO

        # Use grid (no headers) to contain the actual nested Table rows in
        # single column table
        self._status_table = Table.grid(padding=0)
        if study_title:
            self._status_table.title = "STUDY: {}".format(study_title)
        self._status_table.box = box.HEAVY
        self._status_table.show_lines = True
        self._status_table.show_edge = False
        self._status_table.show_footer = True
        self._status_table.collapse_padding = True

        # Uses folding overflow for very long step/workspace names
        self._status_table.add_column("Step", overflow="fold")

        # Note, filter on columns here
        cols = [key for key in self._status_data.keys()
                if (key != 'Step Name' and key != 'Workspace')]

        num_rows = len(self._status_data[cols[0]])

        # Split data into three tables: deails, scheduler, params (optional)
        detail_rows = ['State', 'Job ID', 'Run Time', 'Elapsed Time']
        sched_rows = ['Submit Time',
                      'Start Time',
                      'End Time',
                      'Number Restarts']

        # Setup one table to contain each steps' info
        for row in range(num_rows):
            step_table = Table(
                box=box.SIMPLE_HEAVY,
                show_header=False
            )
            # Dummy columns
            step_table.add_column("key")
            step_table.add_column("val", overflow='fold')

            # Top level contains step name and workspace name, full table width
            step_table.add_row("STEP:",
                               self._status_data['Step Name'][row],
                               style='Step Name')
            step_table.add_row("WORKSPACE:",
                               self._status_data['Workspace'][row],
                               style='Workspace')

            step_table.add_row("", "")  # just a little whitespace

            # Add step details sub table
            step_details = Table.grid(padding=1)
            step_details.add_column("details")

            step_info = Table(title="Step Details",
                              show_header=False,
                              show_lines=True,
                              box=box.HORIZONTALS)

            step_info.add_column("key")
            step_info.add_column("val")
            for nom_row_cnt, detail_row in enumerate(detail_rows):
                if detail_row == 'State':
                    row_style = 'State'
                else:
                    if nom_row_cnt % 2 == 0:
                        row_style = 'row_style'
                    else:
                        row_style = 'row_style'

                step_info.add_row(detail_row,
                                  self._status_data[detail_row][row],
                                  style=row_style)

            step_details.add_column("scheduler")
            step_sched = Table(title="Scheduler Details",
                               show_header=False,
                               show_lines=True,
                               box=box.HORIZONTALS)
            step_sched.add_column("key")
            step_sched.add_column("val")
            for nom_row_cnt, sched_row in enumerate(sched_rows):
                step_sched.add_row(sched_row,
                                   self._status_data[sched_row][row],
                                   style='row_style')  # key in status theme

            # Info and scheduler sub tables are in the same column/row
            step_details.add_row(step_info, step_sched)

            step_table.add_row('', step_details)

            # Add optional parameter table, if step has parameters
            if 'Params' not in self._status_data.keys():
                param_list = []
            else:
                param_list = self._status_data['Params'][row].split(';')

            if len(param_list) > 0 and param_list[0]:
                if len(param_list) % 2 != 0:
                    param_list.append("")

                num_param_rows = int(len(param_list)/2)

                step_params = Table(title="Step Parameters",
                                    show_header=False,
                                    show_lines=True,
                                    box=box.HORIZONTALS)

                # Note col names don't actually matter, just setting styles
                step_params.add_column("name", style="")
                step_params.add_column("val", style="blue", justify="right")
                step_params.add_column("name2", style="")
                step_params.add_column("val2", style="blue", justify="right")

                param_idx = 0
                for param_row in range(num_param_rows):
                    this_row = []
                    for param_str in param_list[param_idx:param_idx+2]:
                        if param_str:
                            this_row.extend(param_str.split(':'))
                        else:
                            this_row.extend(["", ""])

                    param_idx += 2

                    step_params.add_row(*this_row,
                                        style=row_style)

                step_table.add_row('', step_params)

            self._status_table.add_row(step_table, end_section=True)

    def render_to_str(self, theme=None, width=120):
        """Capture output to string"""

        # Apply any theme customization
        if theme:
            for key, value in theme.items():
                self._theme_dict[key] = value

        status_theme = Theme(self._theme_dict)

        _printer = Console(theme=status_theme,
                           file=StringIO(),
                           width=width)
        _printer.print(self._status_table)

        return _printer.file.getvalue()


def iter_status_renderers():
    """Finds all concrete StatusRenderer implementations in this module

    Yields:
        list of (name, class) pairs for all concrete implementations of
        BaseStatusRenderer's in the current module
    """
    def member_is_renderer(member):
        """Helper to test if member is a renderer subclass"""
        return (inspect.isclass(member) and member.__module__ == __name__
                and issubclass(member, BaseStatusRenderer)
                and not inspect.isabstract(member))

    for member in inspect.getmembers(sys.modules[__name__],
                                     member_is_renderer):
        yield member


# Register status layout types
class StatusRendererFactory:
    """Factory for setting up alternate console status rendering formats"""
    def __init__(self):
        self._layouts = {}

        # Auto-registration of implemented renderers in this module
        for layout, renderer in iter_status_renderers():
            self.register_layout(renderer.layout_type, renderer)

    def register_layout(self, layout, renderer):
        """Register layout renderer classes

        Args:
            layout (str): Name of layout to use as key/cli arg
            renderer (BaseStatusRenderer): Any class that is a concrete
                implementation of BaseStatusRenderer api
        """
        self._layouts[layout] = renderer

    def get_renderer(self, layout, disable_theme, disable_pager):
        """Get handle for specific layout renderer to instantiate

        Args:
            layout (str): Name of layout renderer
            disable_theme (bool): True if the user wants to disable themes when displaying status.
                                  False otherwise.
            disable_pager (bool): True if the user wants to disable the pager when displaying status.
                                  False otherwise.

        Returns:
            BaseStatusRenderer: The concrete status renderer class
        """
        renderer = self._layouts.get(layout)

        # Note, need to wrap renderer in try/catch too, or return default val?
        if not renderer:
            raise ValueError(layout)

        return renderer(disable_theme=disable_theme, disable_pager=disable_pager)

    def get_layouts(self):
        """Get list of registered layouts

        Returns:
            list of str: registered status renderer layouts
        """
        return self._layouts.keys()


# Register renderers
status_renderer_factory = StatusRendererFactory()
