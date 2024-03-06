import pytest
from rich.pretty import pprint


@pytest.mark.parametrize(
    "spec_file_name, expected_step_weights",
    [
        (
            "prioritized_hello_bye_parameterized_dfs.yaml",
            {
                "hello_world": 1,
                "bye_world": 2
            }
        ),
        (
            "prioritized_hello_bye_parameterized_bfs.yaml",
            {
                "hello_world": 1,
                "bye_world": 2
            }
        ),
    ],
)
def test_study_weights(study_obj, spec_file_name, expected_step_weights):
    test_study = study_obj(spec_file_name)
    pprint(f"Test study: {test_study}")
    pprint(f"Spec: {spec_file_name}")

    for step_name, step in test_study:
        pprint(f"Step name: {step_name}, step: {step}")
        if step_name in expected_step_weights:
            assert step.weight == expected_step_weights[step_name]


# NOTE: can we refactor to use a shared study fixture instead of redoing it frequently?
@pytest.mark.parametrize(
    "spec_file_name, expected_step_weights",
    [
        (
            "prioritized_hello_bye_parameterized_dfs.yaml",
            {
                "hello_world": 1,
                "bye_world": 2
            }
        ),
        (
            "prioritized_hello_bye_parameterized_bfs.yaml",
            {
                "hello_world": 1,
                "bye_world": 2
            }
        ),
    ],
)
def test_study_stage_weights(study_obj, spec_file_name, expected_step_weights):
    test_study = study_obj(spec_file_name)
    pprint(f"Test study: {test_study}")
    pprint(f"Spec: {spec_file_name}")

    # Prep for staging (need better way to expand the graph without setting up all the things..
    test_study.setup_workspace()
    test_study.configure_study()
    test_study.setup_environment()
    test_out_path, test_exec_graph = test_study.stage()

    base_step_names = list(expected_step_weights.keys())
    for parameterized_step_name, parameterized_step in test_exec_graph:
        pprint(f"Parameterized step name: {parameterized_step_name}, step: {parameterized_step}")
        if not parameterized_step:  # catch source, which is always none
            continue
        # NOTE: really can't get the base step name anymore after staging?
        step_matches = [base_step_name in parameterized_step_name for base_step_name in base_step_names]
        try:
            match = step_matches.index(True)
            base_step_name = base_step_names[match]
            pprint(f"Base step name: {base_step_name}")
            pprint(f"  weight: {parameterized_step.step.weight}")
            assert parameterized_step.step.weight == expected_step_weights[base_step_name]

        except ValueError:
            pprint(f"Couldn't find matching base step name for '{parameterized_step_name}'")
            # Should we assert something here and hard fail?
            continue


@pytest.mark.parametrize(
    "spec_file_name, expected_step_priorities",
    [
        (
            "prioritized_hello_bye_parameterized_dfs.yaml",
            {
                "hello_world": -1,
                "bye_world": -2
            }
        ),
        (
            "prioritized_hello_bye_parameterized_bfs.yaml",
            {
                "hello_world": 1,
                "bye_world": 2
            }
        ),
    ],
)
def test_study_step_priority(study_obj, spec, spec_file_name, expected_step_priorities):
    test_study = study_obj(spec_file_name)
    pprint(f"Test study: {test_study}")
    pprint(f"Spec: {spec_file_name}")

    # Prep for staging (need better way to expand the graph without setting up all the things..
    test_study.setup_workspace()
    test_study.configure_study()
    test_study.setup_environment()
    test_out_path, test_exec_graph = test_study.stage()

    # Load up the execution block to setup prioritization
    study_spec = spec(spec_file_name)
    exec_block = study_spec.execution
    test_exec_graph.set_prioritizer(exec_block)
    prioritizer = test_exec_graph.step_prioritizer

    base_step_names = list(expected_step_priorities.keys())
    for parameterized_step_name, parameterized_step in test_exec_graph:
        pprint(f"Parameterized step name: {parameterized_step_name}, step: {parameterized_step}")
        if not parameterized_step:  # catch source, which is always none
            continue
        # NOTE: really can't get the base step name anymore after staging?
        step_matches = [base_step_name in parameterized_step_name for base_step_name in base_step_names]
        try:
            match = step_matches.index(True)
            base_step_name = base_step_names[match]
            pprint(f"  base step name: {base_step_name}")
            pprint(f"  weight:         {parameterized_step.step.weight}")
            priority = prioritizer.compute_priority(parameterized_step_name, parameterized_step.step)[0]
            pprint(f"  priority:       {priority}")
            assert priority == expected_step_priorities[base_step_name]

        except ValueError:
            pprint(f"Couldn't find matching base step name for '{parameterized_step_name}'")
            # Should we assert something here and hard fail?
            continue
