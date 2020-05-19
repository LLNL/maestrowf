"""This file implements several sampling methods"""

import logging
from maestrowf.datastructures.core import ParameterGenerator

LOGGER = logging.getLogger(__name__)


def _log_assert(test, msg):
    if not(test):
        LOGGER.error(msg)
        raise ValueError(msg)


def _validate_constants_parameters(sampling_dict):
    _log_assert(
        ("parameters" in sampling_dict.keys() or
         "constants" in sampling_dict.keys()),
        "'parameters' or 'constants' must exist")
    if "constants" in sampling_dict.keys():
        _log_assert(
            isinstance(sampling_dict["constants"], dict),
            "'constants' must be a dictionary")


def _validate_parameters_dict(sampling_dict):
    if "parameters" in sampling_dict.keys():
        _log_assert(
            isinstance(sampling_dict["parameters"], dict),
            "'parameters' must be a dictionary for this sampling type")


def _validate_parameters_string(sampling_dict):
    if "parameters" in sampling_dict.keys():
        _log_assert(
            isinstance(sampling_dict["parameters"], str),
            "'parameters' must be a string for this sampling type")


def _validate_sample_dict(samples):
    keys = list(samples[0].keys())
    for row in samples:
        for key in keys:
            _log_assert(
                key in list(row.keys()),
                ("data point " +
                 str(row) + " does not have a value for " +
                 str(key)))


def _convert_dict_to_maestro_params(samples):
    _validate_sample_dict(samples)
    keys = list(samples[0].keys())
    parameters = {}
    for key in keys:
        parameters[key] = {}
        parameters[key]["label"] = str(key) + ".%%"
        values = [sample[key] for sample in samples]
        parameters[key]["values"] = values
    return parameters


def _validate_list_dictionary(sampling_dict):
    _validate_constants_parameters(sampling_dict)
    _validate_parameters_dict(sampling_dict)
    if "parameters" in sampling_dict.keys():
        first = True
        for key, value in sampling_dict["parameters"].items():
            _log_assert(type(key) == str, "parameter labels must be strings")
            _log_assert(type(value) == list, "parameter values must be a list")
            if first:
                sample_length = len(value)
            _log_assert(
                len(value) == sample_length,
                "all sample lists must be the same length")


def list_sample(sampling_dict):
    """
    Return set of samples based on specification in sampling_dict.

    Prototype dictionary:

    sample_type: list
    parameters:
        MASS_1: [ 10, 20, 30 ]
        MASS_2: [ 10, 20, 30 ]
    constants:
        MASS_3: 20
    """
    _validate_list_dictionary(sampling_dict)
    samples = []
    if "constants" in sampling_dict.keys():
        constants = {}
        for key, value in sampling_dict["constants"].items():
            constants[key] = value
    else:
        constants = {}
    if "parameters" in sampling_dict.keys():
        parameters = sampling_dict["parameters"]
        sample_length = len(parameters[next(iter(parameters))])
        for i in range(sample_length):
            sample = constants.copy()
            for key, items in sampling_dict["parameters"].items():
                sample[key] = items[i]
            samples.append(sample)
    else:
        samples.append(constants)
    return _convert_dict_to_maestro_params(samples)


def _validate_cross_product_dictionary(sampling_dict):
    _validate_constants_parameters(sampling_dict)
    if "parameters" in sampling_dict.keys():
        for key, value in sampling_dict["parameters"].items():
            _log_assert(type(key) == str, "parameter labels must be strings")
            _log_assert(type(value) == list, "parameter values must be a list")


def _recursive_cross_product_sample(params, samples=[{}]):
    if params == {}:
        return samples
    key = next(iter(params))
    new_list = []
    for sample in samples:
        for item in params[key]:
            new_sample = sample.copy()
            new_sample[key] = item
            new_list.append(new_sample)
    new_params = params.copy()
    new_params.pop(key)
    return _recursive_cross_product_sample(new_params, samples=new_list)


def cross_product_sample(sampling_dict):
    """
    Return set of samples based on specification in sampling_dict.

    Prototype dictionary:

    sample_type: cross_product
    parameters:
        MASS_1: [ 10, 20 ]
        MASS_2: [ 10, 20 ]
    constants:
        MASS_3: 20
    """
    _validate_cross_product_dictionary(sampling_dict)
    samples = []
    if "constants" in sampling_dict.keys():
        constants = {}
        for key, value in sampling_dict["constants"].items():
            constants[key] = value
    else:
        constants = {}
    if "parameters" in sampling_dict.keys():
        parameters = sampling_dict["parameters"].copy()
        samples = _recursive_cross_product_sample(
                                            parameters,
                                            samples=[constants])
    else:
        samples = [constants]
    LOGGER.info("samples:\n%s", str(samples))
    return _convert_dict_to_maestro_params(samples)


def _validate_column_list_dictionary(sampling_dict):
    _validate_constants_parameters(sampling_dict)
    _validate_parameters_string(sampling_dict)


def column_list_sample(sampling_dict):
    """
    Return set of samples based on specification in sampling_dict.

    Prototype dictionary:

    sample_type: column_list
    constants:
        MASS_3: 20
    parameters: |
        MASS_1   MASS_2
        5        10
        3        7
        12       16
    """
    _validate_column_list_dictionary(sampling_dict)
    samples = []
    if "constants" in sampling_dict.keys():
        constants = {}
        for key, value in sampling_dict["constants"].items():
            constants[key] = value
    else:
        constants = {}
    if "parameters" in sampling_dict.keys():
        rows = sampling_dict["parameters"].split('\n')
        headers = rows.pop(0).split()
        for row in rows:
            data = row.split()
            if len(data) > 0:
                _log_assert(
                    len(data) == len(headers),
                    "Data >>" + str(data) + "<< does not match\n" +
                    "headers >>" + str(headers) + "<<.")
                sample = constants.copy()
                for header, datum in zip(headers, data):
                    sample[header] = datum
                samples.append(sample)
    else:
        samples.append(constants)
    return _convert_dict_to_maestro_params(samples)


def get_custom_generator(env, **kwargs):
    """
    Create a custom populated ParameterGenerator.

    This function supports several sampling methods.

    :params kwargs: A dictionary of keyword arguments this function uses.
    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()
    try:
        SAMPLE_DICTIONARY = kwargs.get(
            "sample_dictionary",
            env.find("SAMPLE_DICTIONARY").value)
    except ValueError:
        raise ValueError("this pgen code requires SAMPLE_DICTIONARY " +
                         "to be defined in the yaml specification")
    try:
        sample_type = SAMPLE_DICTIONARY["sample_type"]
    except ValueError:
        raise ValueError("this pgen code requires SAMPLE_DICTIONARY" +
                         "['sample_type'] to be defined in the yaml " +
                         "specification")
    if sample_type == "list":
        params = list_sample(SAMPLE_DICTIONARY)
        LOGGER.info("params:\n%s", str(params))
    elif sample_type == "cross_product":
        params = cross_product_sample(SAMPLE_DICTIONARY)
        LOGGER.info("params:\n%s", str(params))
    elif sample_type == "column_list":
        params = column_list_sample(SAMPLE_DICTIONARY)
        LOGGER.info("params:\n%s", str(params))
    else:
        raise ValueError("The 'sample_type' of " + sample_type +
                         " is not supported.")

    for key, value in params.items():
        p_gen.add_parameter(key, value["values"], value["label"])

    return p_gen
