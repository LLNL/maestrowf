from maestrowf.datastructures.core import ParameterGenerator
import itertools as iter


def get_custom_generator(env, **kwargs):
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
