from maestrowf import maestro
from maestrowf.conductor import Conductor

import pytest

from rich.pretty import pprint

# NOTE: good place for property testing with hypothesis?
@pytest.mark.parametrize(
    "cli_args, args_are_valid",
    [
        (["--rlimit", "2", 'study_workspace_1'], True),
        (["--rlimit", "2", 'study_workspace_1', 'study_workspace_2'], True),
        (["--rlimit", "2", "--rlimit", "3", 'study_workspace_1'], False),
        (["--rlimit", "2", "--sleep", "30", 'study_workspace_1'], True),
        (["--rlimit", "2", "--sleep", "30", 'study_workspace_1', 'study_workspace_2'], True),
        (["--rlimit", "2", "--sleep", "30", "--sleep", "32", 'study_workspace_1', 'study_workspace_2'], True),
        (["--rlimit", "2", "--sleep", "30", "--sleep", "32", "--sleep", "33", 'study_workspace_1', 'study_workspace_2'], False),
        (["--rlimit", "2", "--sleep", "30", "--sleep", "32", 'study_workspace_1', 'study_workspace_2', 'study_workspace_3'], False),
    ]
)
def test_validate_update_args(cli_args, args_are_valid):
    """
    Test validation of arguments passed to the 'maestro update' cli command
    """
    parser = maestro.setup_argparser()
    maestro_cli = ["update"]

    maestro_cli.extend(cli_args)
    print(f"{maestro_cli=}")
    args = parser.parse_args(maestro_cli)
    # assert args is None
    assert maestro.validate_update_args(args, args.directory) is args_are_valid


@pytest.mark.parametrize(
    "cli_args, expected_expanded_args",
    [
        (
            ["--rlimit", "2", 'study_workspace_1'],
            [{'rlimit': 2, 'throttle': None, 'sleep': None}, ]
        ),
        (
            ["--rlimit", "2", 'study_workspace_1', 'study_workspace_2'],
            [
                {'rlimit': 2, 'throttle': None, 'sleep': None},
                {'rlimit': 2, 'throttle': None, 'sleep': None}
            ]
        ),
        (
            ["--rlimit", "2", "--sleep", "30", 'study_workspace_1'],
            [{'rlimit': 2, 'sleep': 30, 'throttle': None}, ]
        ),
        (
            ["--rlimit", "2", "--sleep", "30", 'study_workspace_1', 'study_workspace_2'],
            [
                {'rlimit': 2, 'sleep': 30, 'throttle': None},
                {'rlimit': 2, 'sleep': 30, 'throttle': None}
            ]
        ),
        (
            ["--rlimit", "2", "--sleep", "30", "--sleep", "32", 'study_workspace_1', 'study_workspace_2'],
            [
                {'rlimit': 2, 'sleep': 30, 'throttle': None},
                {'rlimit': 2, 'sleep': 32, 'throttle': None}
            ],
        ),
    ]
)
def test_expand_update_args(cli_args, expected_expanded_args):
    """
    Test expansion of arguments passed to the 'maestro update' cli command,
    i.e. repeating single values for all study workspaces being updated
    """
    parser = maestro.setup_argparser()
    maestro_cli = ["update"]

    maestro_cli.extend(cli_args)
    print(f"{maestro_cli=}")
    args = parser.parse_args(maestro_cli)
    expanded_args = maestro.expand_update_args(args, args.directory)
    print(f"{args=}")
    print(f"{expanded_args=}")
    print(f"{expected_expanded_args=}")
    assert expanded_args == expected_expanded_args


@pytest.mark.parametrize(
    "cli_args, expected_lock_dict",
    [
        (
            ["--rlimit", "2"],
            {'rlimit': 2, 'throttle': None, 'sleep': None},
        ),
    ]
)
def test_write_update_args(cli_args, expected_lock_dict, tmp_path):
    """
    Test writing and reading of study config updates,
    """
    parser = maestro.setup_argparser()
    maestro_cli = ["update"]

    maestro_cli.extend(cli_args)
    pprint(f"{tmp_path=}")
    maestro_cli.append(str(tmp_path))
    print(f"{maestro_cli=}")
    args = parser.parse_args(maestro_cli)
    print(f"{args=}")
    print(f"{expected_lock_dict=}")

    maestro.update_study_exec(args)

    update_dict = Conductor.load_updated_study_exec(tmp_path)

    assert update_dict == expected_lock_dict
