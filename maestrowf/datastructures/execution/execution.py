import logging
from typing import Dict

from maestrowf.abstracts.execution import PriorityExpr
from rich.pretty import pprint
LOGGER = logging.getLogger(__name__)


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


class StepWeightPriority(PriorityExpr):
    """
    Built in/always on execution priority determined by workflow step
    dependencies. Enables optional depth first priorities to allow
    dependent steps to immediately jump to the head of the line
    Notes
    -----
    Be nice to have a better way to pass around these magic constants for
    easier refactoring..
    """
    def __init__(self, step_order='breadth-first'):

        self.name = 'step_order'
        self.prioritizer_type = 'built-in'  # Enum would be good for this?
        self.step_order = step_order

        if self.step_order == 'breadth-first':
            self._func = self.bfs_priority
        elif self.step_order == 'depth-first':
            self._func = self.dfs_priority
        else:
            raise ValueError(f"Received unknown step order '{self.step_order}'")

    def __call__(self, study_step):
        return self._func(study_step)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def prioritizer_type(self):
        return self._pritoritizer_type

    @prioritizer_type.setter
    def prioritizer_type(self, new_ptype):
        self._prioritizer_type = new_ptype

    @staticmethod
    def bfs_priority(study_step):
        """
        Computes integer priority for breadth first execution of a study. Study
        weights are initialized increasing with depth, so it is returned unchanged
        """
        return study_step.weight

    @staticmethod
    def dfs_priority(study_step):
        """
        Computes integer priority for depth first execution of a study.  Study
        weights are initialized to be increasing with depth, so we invert that
        here to ensure deeper steps jump to head of the queue.
        """
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

        Notes: should we enable per step overrides of global expressions in
        future versions?
        """
        self.priority_expr_names.append(name)
        self.priority_expr_funcs[name] = func

        # Can/should we log the code too?
        LOGGER.info('Registering step prioritizer %s', name)

    def compute_priority(self, name, study_step):
        """
        Compute priority tuple for given study step

        :param name: Name key of the step; key into the graph data struct
        :param study_step: StudyStep object containing resource keys for the expressions
        :returns: tuple of priority values, name for each registered expression

        note: Make the return type a data class that disables comparison on the name?
        """
        priority = []
        for priority_expr_name in self.priority_expr_names:
            priority.append(self.priority_expr_funcs[priority_expr_name](study_step))

        return (*priority, name)


PRIORITY_EXPRESSIONS = {
    'step_order': {
        'prioritizer_type': 'built-in',
        'class': StepWeightPriority
    },
}


def get_built_in_expressions():
    for expr_name, expr_info in PRIORITY_EXPRESSIONS.items():
        if expr_info['prioritizer_type'] == 'built-in':
            yield expr_name


class StepPrioritizationFuncFactory():
    """
    Container for the Specifications Execution Block.  Handles sanitizing
    all the execution parameters and priority expressions and compiling expressions
    for building layered priority orders.
    """
    def __init__(self):
        self.priority_expressions = PRIORITY_EXPRESSIONS

    def get_expression_func(self, expr_name, expr_value):
        if expr_name not in get_built_in_expressions():
            LOGGER.warn("User defined expressions not yet supported. "
                        "Available built in expressions: %s",
                        ' '.join([en for en in get_built_in_expressions()]))
            return None

        if expr_name not in self.priority_expressions:
            # Place holder for custom expression building
            LOGGER.warn("Unknown priority expression '%s' requested.",
                        expr_name)
            LOGGER.warn("Skipping custom expression construction for '%s': not"
                        " yet supported",
                        expr_name)
            return None

        LOGGER.info("Returning func for '%s' priority expression", expr_name)
        return self.priority_expressions[expr_name]['class'](expr_value)


class ExecutionBlock():
    """
    Container for the Specifications Execution Block.  Handles sanitizing
    all the execution parameters and priority expressions and compiling expressions
    for building layered priority orders.
    """
    step_prioritization_factory = None

    def __init__(self, execution_expressions=None):
        self.step_prioritization_factory = StepPrioritizationFuncFactory()

        #  Need better way to keep these in sync with spec's schema
        self.exec_list = execution_expressions

        # Ensure step_order is included.  if not, prepend it
        if not self.exec_list:
            self.exec_list = [
                {'step_order': 'breadth-first'}
            ]
        elif not any(['step_order' in pexpr for pexpr in self.exec_list]):
            self.exec_list = [{'step_order': 'breadth-first'}] + self.exec_list

        self.step_prioritizer = StepPrioritizer()

        for expr in self.exec_list:
            # note: likely be nicer to make these actual objects during spec parsing..
            expr_name = list(expr.keys())[0]
            expr_value = expr[expr_name]
            # NOTE: may be worth while to separate creation/validation to a separate
            #       step from retrieval?
            priority_func = self.step_prioritization_factory.get_expression_func(expr_name, expr_value)
            if not priority_func:
                continue

            self.step_prioritizer.register_priority_expr(
                expr_name,
                priority_func
            )

    def get_step_prioritizer(self):
        return self.step_prioritizer
