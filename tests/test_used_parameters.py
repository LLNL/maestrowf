from maestrowf.datastructures.core.parameters import ParameterGenerator
from maestrowf.datastructures.core.study import StudyStep


def test_get_used_parameters_no_prefix_collision():
    pgen = ParameterGenerator()
    pgen.add_parameter("N", [1, 2], "N.%%")
    pgen.add_parameter("NP", [4, 8], "NP.%%")

    step = StudyStep()
    step.run["cmd"] = "srun -n $(NP) ./solver"

    # A step that only uses $(NP) must not also pull in $(N) via prefix match.
    assert pgen.get_used_parameters(step) == {"NP"}
