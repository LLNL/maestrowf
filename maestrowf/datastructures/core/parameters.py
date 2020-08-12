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
This module contains classes related to parameters and parameter generation.

The goal of this module is to abstract away how parameters are generated from
the user. In terms of parameters the only things a user should see is the
ParameterGenerator that offers an API for managing parameters and generates
individual Combinations (the second object a user should ever see).
"""
from collections import OrderedDict
import logging
import re

logger = logging.getLogger(__name__)


class Combination(object):
    """
    Class representing a combination of parameters.

    This class represents a combination of parameters generated by a class of
    type ParameterGenerator. The only time a user should ever get an instance
    of a Combination from the ParameterGenerator is when a combination of
    parameters is VALID.
    """

    def __init__(self, token="$"):
        """
        Initialize an empty Combination class.

        A Combination comes packed with the following:
            - Corresponding values for each parameter in the instance.
            - A name for each parameter in instance.
            - Labels for each parameter-value combination in the instance.

        The 'token' method parameter defines the character(s) that are expected
        in front of user parameterized values in strings when an instance of
        a Combination is applied. For example, assume that we have an instance
        'c' of the Combination class that has had the parameter 'PARAM1' added.
        'PARAM1' is named 'COMPONENT1' and 'token' is left at its default value
        of '$'. 'PARAM1' has some arbitrary value that was set. In order to
        substitute the different variations of 'PARAM1' in a string when the
        apply method is called, the user would include the following mark up:

        * The value of 'PARAM1': '$(PARAM1)'
        * The label of 'PARAM1': '$(PARAM1.label)'
        * The name of 'PARAM1':  '$(PARAM1.name)'

        :param token: Token expected to be found in front of a parameter.
        """
        self._params = {}
        self._labels = OrderedDict()
        self._names = {}
        self._token = token

    def add(self, key, name, value, label):
        """
        Add a parameter to the Combination object.

        :param key: Parameter key that identifies a replacement.
        :param name: Custom name that identifies a parameter.
        :param value: Value of the parameter in this combination.
        :param label: Value of the parameter label for this combination.
        """
        # For the combination being added, assign the expected parameterized
        # strings that the user would substitute in for.
        # Parameterized value:  <self.token>(<key>)
        logger.debug("Adding parameter value to Combination with args: %s",
                     [key, name, value, label])
        var = "{}({})".format(self._token, key)
        logger.debug('Parameter value: %s = %s', var, value)
        self._params[var] = value
        # Parameterized label: <self.token>(<key>.label)
        var = "{}({}.label)".format(self._token, key)
        logger.debug('Label value: %s = %s', var, label)
        self._labels[var] = label
        # Parameterized name: <self.token>(<key>.name)
        var = "{}({}.name)".format(self._token, key)
        logger.debug('Name value: %s = %s', var, name)
        self._names[var] = name

    def __str__(self):
        """
        Generate the string representation of a Combination object.

        :returns: A string representing the combination.
        """
        return ".".join(self._labels.values())

    def get_param_string(self, params):
        """
        Get the combination string for the specified parameters.

        :param params: A set of parameters to be used in the string.
        :returns: A string containing the labels for the parameters in params.
        """
        combo_str = []
        for item in sorted(params):
            var = "{}({}.label)".format(self._token, item)
            combo_str.append(self._labels[var])

        return ".".join(combo_str)

    def apply(self, item):
        """
        Apply the combination to an item.

        :param item: String that may contain parameters to be substituted.
        :returns: String equal to item, except with parameters replaced.
        """
        # Apply the Combination's labels to the item.
        # These are substrings within item that are represented by the format
        # <self.token>(<key>.label)
        for key, value in self._labels.items():
            item = item.replace(key, str(value))

        # Apply the Combination's values to the item.
        # These are substrings within item that are represented by the format
        # <self.token>(<key>)
        for key, value in self._params.items():
            item = item.replace(key, str(value))

        # Apply the Combination's names to the item.
        # These are substrings within item that are represented by the format
        # <self.token>(<key>.name)
        for key, name in self._names.items():
            item = item.replace(key, str(name))

        # Return the item after the Combination has applied itself to it. The
        # parameter item is simply reused since all we're doing is replacing
        # substrings.
        return item

    @property
    def param_vals(self):
        """
        Return dict of parameter values
        """
        return self._params

    @property
    def param_labels(self):
        """
        Return dict of parameter labels
        """
        return self._labels
    
class ParameterGenerator:
    """
    Class for containing parameters and generating combinations.

    The goal of this class is to provide one centralized location for managing
    and storing parameters. This implementation of the ParameterGenerator,
    currently, is very basic. It takes lists of parameters and uses those to
    construct combinations, meaning that if you were to view this as an Excel
    table, you would have a row for each valid combination you wanted to study.

    The other goal is to make it so that by having the ParameterGenerator
    manage parameters, functionality can be added without affecting how the
    end user interacts with this class. The ParameterGenerator has an Iterator
    defined and will generate each combination one by one. The end user should
    NEVER SEE AN INVALID COMBINATION. Because this class generates the
    combinations as specified by the parameters added (eventually with types
    or enforced inheritence), and eventually constraints, it opens up being
    able to quietly change how this class generates its combinations.

    Easily convert studies to other types of studies. Because the API doesn't
    change from its nice Pythonic style, you can in theory swap out a
    ParameterGenerator that performs completely differently. All of a sudden,
    you can get the following for simply deriving from this class:

    * Uncertainty Quantification (UQ): Add the ability to statistically
      sample parameters behind the scenes. Let the ParameterGenerator
      constraint solve behind the scenes and return the Combination
      objects it was going to return in the first place. If you can't
      find a valid sampling, just return nothing and the study won't run.
    * Boundary and constraint testing: Like UQ above, hide the solving
      from the user. Simply add parameters to be constraint solved on
      behind the API and all the user sees is combinations on the frontend.

    Ideally, all parameter generation schemes should boil down as follows:

    1. Derive from this class, add constraint solving.
    2. Construct a study how you would otherwise do so, just use
       the new ParameterGenerator and add parameters.
    3. Setup, stage, and execute your study.
    4. Profit.
    """

    def __init__(self, token="$", ltoken="%%"):
        """
        Initialize an empty ParameterGenerator object.

        The ParameterGenerator is instantiated with two token values, one for
        parameters and one for labels. The 'token' parameter represents the
        character(s) expected in front of parameterized strings. For example,
        if 'token' is left at its default of '$' and we have a parameter named
        'COMP1', then the instance of the ParameterGenerator will replace the
        value '$(COMP1)' in any item passed to the apply method. The 'ltoken'
        parameter functions in much the same way, except that instead of
        substituting for a parameter, this character(s) is what is found in a
        parameter label. The label for the parameter 'COMP1' is specified as
        '$(COMP.label)' where the label may have a value of 'COMP1.%%' (where
        %% is the default value of ltoken). For any combination, '%%' will be
        replaced by the value of the parameter 'COMP1' for that given instance
        when the label is specified in a item.

        :param token: Leading token that denotes a parameter (Default: '$').
        :param ltoken: Token that represents where to place a value in a label
            (Default: '%%').
        """
        self.parameters = OrderedDict()
        self.labels = {}
        self.names = {}
        self.label_token = ltoken
        self.token = token

        self.length = 0

    def add_parameter(self, key, values, label=None, name=None):
        """
        Add a parameter to the ParameterGenerator.

        Currently, all parameters added to a ParameterGenerator instance must
        have a list of values that are the same length. Future improvements
        will add the ability to specify either types of parameters or provide
        different ParameterGenerators derivations that have unique behavior.

        :param key: Parameter key to find for replacement.
        :param values: List of values the parameter can take.
        :param label: Label string for labeling the parameter.
        :param name: Custom name for identifying parameter.
        """
        if key in self.parameters:
            logger.warning("'%s' already in parameter set. Overriding.", key)

        self.parameters[key] = values
        if self.length == 0:
            self.length = len(values)

        elif len(values) != self.length:
            error = "Length of values list must be the same size as " \
                    "the other parameters that exist in the " \
                    "generators. Length of '{}' is {}. Aborting." \
                    .format(name, len(values))
            logger.exception(error)
            raise ValueError(error)

        if label:
            self.labels[key] = label
        else:
            self.labels[key] = "{}.{}".format(key, self.label_token)

        if name:
            self.names[key] = name
        else:
            self.names[key] = key

    def __iter__(self):
        """
        Return the iterator for the ParameterGenerator.

        :returns: Iterator for walking parameter combinations.
        """
        return self.get_combinations()

    def __bool__(self):
        """
        Override for the __bool__ operator.

        :returns: True if the ParameterGenerator instance has values, False
            otherwise.
        """
        return bool(self.parameters)

    __nonzero__ = __bool__

    def get_combinations(self):
        """
        Generate all combinations of parameters.

        :returns: A generator with all combinations of parameters.
        """
        for i in range(0, self.length):
            combo = Combination()
            for key in self.parameters.keys():
                pvalue = self.parameters[key][i]
                if isinstance(self.labels[key], list):
                    tlabel = self.labels[key][i]
                else:
                    tlabel = self.labels[key].replace(self.label_token,
                                                      str(pvalue))
                name = self.names[key]
                combo.add(key, name, pvalue, tlabel)
            yield combo

    def _get_used_parameters(self, item, params):
        """
        Find the parameters used by an item in a StudyStep.

        :param item: The item to search for parameters.
        :param params: The current set of found parameters.
        """
        if not item:
            return
        elif isinstance(item, int):
            return
        elif isinstance(item, str):
            for key in self.parameters.keys():
                _ = r"\{}\({}\.*\w*\)".format(self.token, key)
                matches = re.findall(_, item)
                if matches:
                    params.add(key)
        elif isinstance(item, list):
            for each in item:
                self._get_used_parameters(each, params)
        elif isinstance(item, dict):
            for each in item.values():
                self._get_used_parameters(each, params)
        else:
            msg = "Encountered an object of type '{}'. Expected a str, list," \
                  " int, or dict.".format(type(item))
            logger.error(msg)
            raise ValueError(msg)

    def get_used_parameters(self, step):
        """
        Return the parameters used by a StudyStep.

        :param step: A StudyStep instance to be checked.
        :returns: A set of the parameter names used within the step parameter.
        """
        params = set()
        self._get_used_parameters(step.__dict__, params)
        return params

    def get_metadata(self):
        """
        Produce metadata for the parameters in a generator instance.

        :returns: A dictionary containing metadata about the instance.
        """
        meta = {}
        for combo in self.get_combinations():
            meta[str(combo)] = {}
            meta[str(combo)]["params"] = combo._params
            meta[str(combo)]["labels"] = combo._labels

        return meta
