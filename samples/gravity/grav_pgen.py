from maestrowf.datastructures.core import ParameterGenerator
from random import randint

CELESTIAL_BODIES = [
    "Sun", "Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn",
    "Uranus", "Neptune", "Pluto"
]


def get_custom_generator(env, **kwargs):
    """
    Create a custom ParameterGenerator for the gravity example that
    samples the gravitation field of random pairs.
    :returns: A ParameterGenerator populated with parameters.
    """
    p_gen = ParameterGenerator()

    n_samples = int(env.find("SAMPLES").value)
    num_bodies = len(CELESTIAL_BODIES)
    samples = []

    for i in range(n_samples):
        a = CELESTIAL_BODIES[randint(0, (num_bodies - 1))]
        b = a

        while b == a:
            b = CELESTIAL_BODIES[randint(0, (num_bodies - 1))]

        samples.append((a, b))
  
    values_p1 = [x[0] for x in samples]
    values_p2 = [x[1] for x in samples]

    p_gen.add_parameter("PLANET1", values_p1, "PLANET1.%%")
    p_gen.add_parameter("PLANET2", values_p2, "PLANET2.%%")

    return p_gen