"""An example file that produces a custom ParameterGenerator."""

from maestrowf.datastructures.core import ParameterGenerator


def get_custom_generator(env, **kwargs):
    """
    Create a custom populated ParameterGenerator.

    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()
    key = "TEST"
    names = ["test1", "test2", "test3", "test4", "test5"]
    values = ["1", "2", "3", "4", "5"]
    label = "TEST.{}"

    for i in range(0, len(names)):
        p_gen.add_parameter(key, values[i], label, names[i])

    return p_gen
