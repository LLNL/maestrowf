"""An example file that produces a custom parameters for the LULESH example."""

from random import randint

from maestrowf.datastructures.core import ParameterGenerator


def get_custom_generator(**kwargs):
    """
    Create a custom populated ParameterGenerator.

    This function recreates the exact same parameter set as the sample LULESH
    specifications. The point of this file is to present an example of how to
    generate custom parameters.

    :params kwargs: A dictionary of keyword arguments this function uses.
    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()
    trials = int(kwargs.get("trials"))
    size_min = int(kwargs.get("smin"))
    size_max = int(kwargs.get("smax"))
    iterations = int(kwargs.get("iter"))
    params = {
        "TRIAL": {
            "values": [i for i in range(1, trials)],
            "label": "TRIAL.%%"
        },
        "SIZE": {
            "values": [randint(size_min, size_max) for i in range(1, trials)],
            "label": "SIZE.%%"
        },
        "ITERATIONS": {
            "values": [iterations for i in range(1, trials)],
            "label": "ITERATIONS.%%"
        }
    }

    for key, value in params.items():
        p_gen.add_parameter(key, value["values"], value["label"])

    return p_gen
