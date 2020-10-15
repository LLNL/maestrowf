from maestrowf.datastructures.core import ParameterGenerator
import numpy as np


def chebyshev_dist(var_range, num_pts):
    """
    Helper function for generating Chebyshev points in a specified range.

    :params var_range: Length 2 list or tuple defining the value range
    :params num_pts: Integer number of points to generate
    :returns: ndarrays of the Chebyshev x points, and the corresponding y
              values of the circular mapping
    """
    r = 0.5*(var_range[1] - var_range[0])

    angles = np.linspace(np.pi, 0.0, num_pts)
    xpts = r*np.cos(angles) + r
    ypts = r*np.sin(angles)

    return xpts, ypts


def get_custom_generator(env, **kwargs):
    """
    Create a custom populated ParameterGenerator.
    This function generates a 1D distribution of points for a single variable,
    using the Chebyshev points scaled to the requested range.
    The point of this file is to present an example of using external libraries
    and helper functions to generate parameter value distributions.  This
    technique can be used to build reusable/modular sampling libraries that
    pgen can hook into.

    :params env: A StudyEnvironment object containing custom information.
    :params kwargs: A dictionary of keyword arguments this function uses.
    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()

    # Unpack any pargs passed in
    x_min = int(kwargs.get('X_MIN', '0'))
    x_max = int(kwargs.get('X_MAX', '1'))
    num_pts = int(kwargs.get('NUM_PTS', '10'))

    x_pts, ypts = chebyshev_dist([x_min, x_max], num_pts)

    params = {
        "X": {
            "values": list(x_pts),
            "label": "X.%%"
        },
    }

    for key, value in params.items():
        p_gen.add_parameter(key, value["values"], value["label"])

    return p_gen
