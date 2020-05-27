"""An example file that produces a custom parameters for the LULESH example."""

from random import randint, seed

from maestrowf.datastructures.core import ParameterGenerator


def get_custom_generator(env, **kwargs):
    """
    Create a custom populated ParameterGenerator.
    This function adapts the LULESH custom generator to randomly generate
    values for the SIZE parameter within a prescribed range.  An optional
    seed is included, which if present on the command line or in the spec's
    env block will allow reproducible random values.

    :params env: A StudyEnvironment object containing custom information.
    :params kwargs: A dictionary of keyword arguments this function uses.
    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()
    trials = int(kwargs.get("trials", env.find("TRIALS").value))
    size_min = int(kwargs.get("smin", env.find("SMIN").value))
    size_max = int(kwargs.get("smax", env.find("SMAX").value))
    iterations = int(kwargs.get("iter", env.find("ITER").value))
    r_seed = kwargs.get("seed", env.find("SEED").value)

    seed(a=r_seed)

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
