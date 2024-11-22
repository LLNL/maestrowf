import argparse
from maestrowf import maestro
import pytest

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
