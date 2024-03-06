import sys

if sys.version_info < (3, 8):
    from typing_extensions import Protocol
else:
    from typing import Protocol

# TODO: fix circular imports so we can use type hint
# from maestrowf.datastructures.core.study import StudyStep


class PriorityExpr(Protocol):
    """
    Defines api for Priority Expressions for study steps.
    """
    def __call__(self, study_step):
        """
        Compute priority for a study step

        :param study_step: StudyStep instance to compute priority for
        :returns: any type implementing __lt__ and __eq__.  Must be consistent
                  type for all parameterized instances of this step
        """
        ...
