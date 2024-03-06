from typing import Dict

from maestrowf.abstracts.execution import PriorityExpr

priority_expressions = {}


class StepWeightPriorityBF(PriorityExpr):
    """
    Computes integer priority for breadth first execution of a study. Study
    weights are initialized increasing with depth, so it is returned unchanged
    """
    def __call__(self, study_step):
        return study_step.weight


class StepWeightPriorityDF(PriorityExpr):
    """
    Computes integer priority for depth first execution of a study.  Study
     weights are initialized to be increasing with depth, so we invert that
    """
    def __call__(self, study_step):
        return -1*study_step.weight


class StepPrioritizer:
    """
    Container of expressions used for computing tuples for manipulating step
    execution priority.
    """
    def __init__(self):
        """"""
        # step_priority_parts = []
        self.priority_expr_names = []    # Use this for controlling expr application ordering
        self.priority_expr_funcs = {}

    def register_priority_expr(self, name: str, func: PriorityExpr, override: bool = False):
        """
        Register a new expression for computing a step's priority
        :param name: expression name/id
        :param func: PriorityExpr, returning a type implementing __lt__ and __eq__

        Notes: expression name can be used to enable per step overrides of global
        expressions in future versions.  Should name be owned by the expression
        objects?
        """
        if name in priority_expressions and not override:
            return

        if name not in priority_expressions:
            self.priority_expr_names.append(name)

        self.priority_expr_funcs[name] = func

    def compute_priority(self, name, study_step):
        """
        Compute priority tuple for given study step

        :param name: Name key of the step; key into the graph data struct
        :param study_step: StudyStep object containing resource keys for the expressions
        :returns: tuple of priority values, name for each registered expression

        note: Make the return type a data class that disables comparison on the name?
        """
        priority = []
        for priority_expr in self.priority_expr_names:
            priority.append(self.priority_expr_funcs[priority_expr](study_step))

        return (*priority, name)


class ExecutionBlock():
    """
    Container for the Specifications Execution Block.  Handles sanitizing
    all the execution parameters and priority expressions and compiling expressions
    for building layered priority orders.
    """
    step_prioritization_factory = None
    
    def __init__(self, execution_dict=None):
        """
        
        """
        self.exec_dict = {'step_order': 'breadth-first'}

        if execution_dict and isinstance(execution_dict, Dict):
            self.exec_dict.update(execution_dict)

        self.step_order = self.exec_dict['step_order']

        self.step_prioritizer = StepPrioritizer()

        # NOTE: This is simple for now, but more composable expressions will be
        # parsed/built here in the future

        # Set expression for step order, which is always on
        if self.step_order == 'breadth-first':
            self.step_prioritizer.register_priority_expr(
                'step_order',
                StepWeightPriorityBF()
            )
        elif self.step_order == 'depth-first':
            self.step_prioritizer.register_priority_expr(
                'step_order',
                StepWeightPriorityDF()
            )
        else:
            raise ValueError(f"Received unknown step order '{self.step_order}'")

    def get_step_prioritizer(self):
        return self.step_prioritizer
