from maestrowf.datastructures.core import ParameterGenerator
import numpy as np


def chebyshev_dist(var_range, num_pts):
    r = 0.5*(var_range[1] - var_range[0])

    angles = np.linspace(np.pi, 0.0, num_pts)
    xpts = r*np.cos(angles) + r
    ypts = r*np.sin(angles)

    return xpts, ypts


def get_custom_generator(env, **kwargs):
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
