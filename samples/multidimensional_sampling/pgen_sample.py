"""This file implements several sampling methods"""

import yaml
import random
import glob
import time
from math import *

import logging
from maestrowf.datastructures.core import ParameterGenerator

from contextlib import suppress

PANDAS_PLUS = False
with suppress(ModuleNotFoundError):
    import pandas as pd
    import numpy as np
    import scipy.spatial as spatial
    from sklearn.tree import DecisionTreeRegressor
    from sklearn.neighbors import KDTree
    PANDAS_PLUS = True


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
    return samples


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
    return samples


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
    return samples


def _validate_best_candidate_dictionary(sampling_dict):
    _validate_constants_parameters(sampling_dict)
    _validate_parameters_dict(sampling_dict)
    _log_assert(
        type(sampling_dict["num_samples"]) == int,
        "'num_samples' must exist and be an integer")
    _log_assert(
        isinstance(sampling_dict["parameters"], dict),
        "'parameters' must exist and be a dictionary")
    if 'previous_samples' in sampling_dict.keys():
        pass
        # TTD: validate that file exists and that it
        # contains same parameters as `parameters`
    for key, value in sampling_dict["parameters"].items():
        _log_assert(type(key) == str, "parameter labels must be strings")
        _log_assert(
            str(value["min"]).isnumeric(),
            "parameter must have a numeric minimum")
        _log_assert(
            str(value["max"]).isnumeric(),
            "parameter must have a numeric maximum")

def down(samples, sampling_dict):
    """
    Downselect samples based on specification in sampling_dict.
        
    Prototype dictionary:

    num_samples: 30
    previous_samples: samples.csv # optional
    parameters:
        MASS_1:
            min: 10
            max: 50
        MASS_2:
            min: 10
            max: 50
    """
    _log_assert(
        PANDAS_PLUS,
        "This function requires pandas, numpy, scipy & sklearn packages")
    _validate_best_candidate_dictionary(sampling_dict)
    
    df = pd.DataFrame.from_dict(samples)
    columns=sampling_dict["parameters"].keys()
    ndims = len(columns)
    candidates = df[columns].values.tolist()
    num_points = sampling_dict["num_samples"]
 
    if not('previous_samples' in sampling_dict.keys()):
        sample_points=[]
        sample_points.append(candidates[0])
        new_sample_points=[]
        new_sample_points.append(candidates[0])
        new_sample_ids = []
        new_sample_ids.append(0)
        n0 = 1
    else:
        try:
            previous_samples = pd.read_csv(sampling_dict["previous_samples"])  
        except ValueError:
            raise ValueError("Error opening previous_samples datafile:" +
                  sampling_dict["previous_samples"])
        sample_points=previous_samples[columns].values.tolist()
        new_sample_points=[]
        new_sample_ids = []
        n0 = 0
        
    mins = np.zeros(ndims)
    maxs = np.zeros(ndims)
    for j in range(ndims):
        mins[j] = 1.0e30
        maxs[j] = -1.0e30
    
    for i in range(len(candidates)):
        ppi = candidates[i]
        for j in range(ndims):
            mins[j] = min(ppi[j],mins[j])
            maxs[j] = max(ppi[j],maxs[j])
    print("extrema for new input_labels: ",mins,maxs)
    print("down sampling to %d best candidates from %d total points."%(
        num_points,len(candidates)))
    bign = len(candidates)
    bigtree = spatial.KDTree(candidates)
 
    for n in range(n0,num_points):
        px = np.asarray(sample_points)
        tree = spatial.KDTree(px)
        j = bign
        d = 0.0
        for i in range(1,bign):
            pos = candidates[i]
            dist = tree.query(pos)[0]
            if dist > d:
                j = i
                d = dist
        if j==bign:
            raise ValueError("Something went wrong!")
        else:
            new_sample_points.append(candidates[j])
            sample_points.append(candidates[j])
            new_sample_ids.append(j)
    
    new_samples_df = pd.DataFrame(columns=df.keys().tolist())
    for n in range(len(new_sample_ids)):
        new_samples_df=new_samples_df.append(df.iloc[new_sample_ids[n]])

    return new_samples_df.to_dict(orient='records')

def random_sample(sampling_dict):
    """
    Return set of random samples based on specification in sampling_dict.
    
    Prototype dictionary:

    num_samples: 30
    previous_samples: samples.csv # optional
    parameters:
        MASS_1:
            min: 10
            max: 50
        MASS_2:
            min: 10
            max: 50
    """
    _validate_best_candidate_dictionary(sampling_dict)
    # create initial input data
    random_list = []
    min_dict = {}
    range_dict = {}
    for key, value in sampling_dict["parameters"].items():
        min_dict[key] = value["min"]
        range_dict[key] = value["max"] - value["min"]
    for i in range(sampling_dict["num_samples"]):
        random_dictionary = {}
        for key, value in sampling_dict["parameters"].items():
            random_dictionary[key] = min_dict[key] + random.random() * range_dict[key]
        random_list.append(random_dictionary)
    return(random_list)


def best_candidate_sample(sampling_dict, over_sample_rate=10):
    """
    Return set of best candidate samples based on specification in sampling_dict.

    Prototype dictionary:

    sample_type: best_candidate
    num_samples: 30
    # previous_samples: samples.csv
    constants:
        MASS_3: 20
    parameters:
        MASS_1:
            min: 10
            max: 50
        MASS_2:
            min: 10
            max: 50
    """
    _log_assert(
        PANDAS_PLUS,
        "This function requires pandas, numpy, scipy & sklearn packages")
    _validate_best_candidate_dictionary(sampling_dict)
    new_sampling_dict = sampling_dict.copy()
    new_sampling_dict["num_samples"] *= over_sample_rate
    new_random_sample = random_sample(new_sampling_dict)

    samples = down(new_random_sample, sampling_dict)
    if "constants" in sampling_dict.keys():
        for sample in samples:
            for key, value in sampling_dict["constants"].items():
                sample[key] = value

    return samples


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
        samples = list_sample(SAMPLE_DICTIONARY)
    elif sample_type == "cross_product":
        samples = cross_product_sample(SAMPLE_DICTIONARY)
    elif sample_type == "column_list":
        samples = column_list_sample(SAMPLE_DICTIONARY)
    elif sample_type == "best_candidate":
        samples = best_candidate_sample(SAMPLE_DICTIONARY)
    else:
        raise ValueError("The 'sample_type' of " + sample_type +
                         " is not supported.")

    params = _convert_dict_to_maestro_params(samples)
    LOGGER.info("params:\n%s", str(params))

    for key, value in params.items():
        p_gen.add_parameter(key, value["values"], value["label"])

    return p_gen
