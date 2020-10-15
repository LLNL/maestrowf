from maestrowf.datastructures.core import ParameterGenerator
import itertools as iter


def get_custom_generator(env, **kwargs):
    """
    Create a custom populated ParameterGenerator.
    This function recreates the exact same parameter set as the sample LULESH
    specifications. The difference here is that itertools is employed to
    programmatically generate the samples instead of manually writing out
    all of the combinations.
    :params env: A StudyEnvironment object containing custom information.
    :params kwargs: A dictionary of keyword arguments this function uses.
    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()

    sizes = (10, 20, 30)
    iterations = (10, 20, 30)

    size_values = []
    iteration_values = []
    trial_values = []

    for trial, param_combo in enumerate(iter.product(sizes, iterations)):
        size_values.append(param_combo[0])
        iteration_values.append(param_combo[1])
        trial_values.append(trial)

    params = {
        "TRIAL": {
            "values": trial_values,
            "label": "TRIAL.%%"
        },
        "SIZE": {
            "values": size_values,
            "label": "SIZE.%%"
        },
        "ITER": {
            "values": iteration_values,
            "label": "ITER.%%"
        },
    }

    for key, value in params.items():
        p_gen.add_parameter(key, value["values"], value["label"])

    return p_gen
