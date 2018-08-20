"""An example file that produces a custom parameters for the LULESH example."""

from maestrowf.datastructures.core import ParameterGenerator


def get_custom_generator():
    """
    Create a custom populated ParameterGenerator.

    This function recreates the exact same parameter set as the sample LULESH
    specifications. The point of this file is to present an example of how to
    generate custom parameters.

    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()
    params = {
        "TRIAL": {
            "values": [i for i in range(1, 10)],
            "label": "TRIAL.%%"
        },
        "SIZE": {
            "values": [10, 10, 10, 20, 20, 20, 30, 30, 30],
            "label": "SIZE.%%"
        },
        "ITERATIONS": {
            "values": [10, 20, 30, 10, 20, 30, 10, 20, 30],
            "label": "ITERATIONS.%%"
        }
    }

    for key, value in params.items():
        p_gen.add_parameter(key, value["values"], value["label"])

    return p_gen
