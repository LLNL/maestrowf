from typing import Protocol

# TODO: fix circular imports so we can use type hint
# from maestrowf.datastructures.core.study import StudyStep


class PriorityExpr(Protocol):
    """
    Defines api for Priority Expressions for study steps.

    :returns: Callable, returning type implementing __lt__ and __eq__
    """
    def __call__(self, study_step):
        ...
