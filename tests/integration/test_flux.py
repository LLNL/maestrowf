import os
import logging
from pathlib import Path
from shutil import rmtree
from subprocess import run
import time
from datetime import datetime
# import tempfile

import yaml

import pytest

log = logging.getLogger("pytest")

# from pytest import raises
# from contextlib import nullcontext
from rich.console import Console
from maestrowf.interfaces.script.fluxscriptadapter import FluxScriptAdapter
from maestrowf.interfaces import ScriptAdapterFactory
from maestrowf.specification.yamlspecification import YAMLSpecification

console = Console()
# Tag every test in this file as requiring flux
pytestmark = [pytest.mark.sched_flux,
              pytest.mark.integration,]


def retcode_is_non_zero(x):
    """Predicate for testing non-zero retcodes for clearer pytest outputs"""
    return x != 0


def retcode_is_zero(x):
    """Predicate for testing zero retcodes for clearer pytest outputs"""
    return x == 0


@pytest.mark.parametrize(
    "spec_name, queue, bank, tmp_study_dir, flux_adaptor_version, test_instance_level, expected_conductor_state, retcode_predicate, expected_step_finished",
    [
        (                       # Standalone batch jobs, valid queue
            "hello_bye_parameterized_flux.yaml",
            "pdebug",
            "guests",
            "HELLO_BYE_FLUX",
            "0.49.0",
            0,
            True,
            retcode_is_zero,
            True
        ),
        (                       # Standalone batch jobs, invalid queue
            "hello_bye_parameterized_flux.yaml",
            "invalid_queue",
            "guests",
            "HELLO_BYE_FLUX_INVALID_QUEUE",
            "0.49.0",
            0,
            False,
            retcode_is_non_zero,                  # Why is the actual number 2?
            False
        ),
        (                       # Standalone batch jobs, invalid bank
            "hello_bye_parameterized_flux.yaml",
            "pdebug",
            "the-bad-bank",
            "HELLO_BYE_FLUX_INVALID_BANK",
            "0.49.0",
            0,
            False,              # Complete with failures!
            retcode_is_non_zero,
            False
        ),
        (                       # Allocation packing, autouse anonymous queue
            "hello_bye_parameterized_flux.yaml",
            "in_alloc_queue",
            "pdebug",           # Expected no-op here
            "HELLO_BYE_FLUX_NEST",
            "0.49.0",
            1,
            True,
            retcode_is_zero,
            True                # Default anonymous queue should be detected
        ),
    ]
)
def test_hello_world_flux(samples_spec_path,
                          tmp_path,  # Pytest tmp dir fixture: Path()
                          check_study_success,
                          check_all_steps_finished,
                          spec_name,
                          queue,
                          bank,
                          tmp_study_dir,
                          flux_adaptor_version,
                          test_instance_level,
                          expected_conductor_state,
                          retcode_predicate,
                          expected_step_finished):
    """
    Run integration tests using the flux scheduler.
    """
    spec_path = samples_spec_path(spec_name)

    tmp_outdir = tmp_path / tmp_study_dir

    # tmp_outdir = os.path.abspath(os.path.join(os.getcwd(), tmp_study_dir))
    # tmp_outdir = Path(tmp_study_dir)
    # Clean up detritus from failed tests
    if os.path.exists(tmp_outdir):
        console.rule(f"Existing study workspace found")
        console.print(f"Clearing: {tmp_outdir}")

        rmtree(tmp_outdir, ignore_errors=True)  # recursively delete workspace
        console.print(f"{tmp_outdir} exisits: {tmp_outdir.exists()}")
        for file in tmp_outdir.parent.iterdir():
            console.print(f"{file.resolve()}")

    # if not tmp_outdir.exists():
    #     tmp_outdir.mkdir()

    # TODO: revisit this, looking at letting yamlspecs serialize themselves,
    # and explore alternatives for perturbing specs during testing without
    # cluttering samples dir with stuff that's meant to fail
    with open(spec_path, 'r') as raw_yaml_file:
        spec = yaml.safe_load(raw_yaml_file)

    spec['batch']['queue'] = queue
    spec['batch']['bank'] = bank

    tmp_spec_path = tmp_path / spec_name
    with open(tmp_spec_path, 'w') as updated_yaml_spec_file:
        yaml.safe_dump(spec, updated_yaml_spec_file, default_flow_style=False, sort_keys=False)

    spec = YAMLSpecification.load_specification(tmp_spec_path)
    # spec.batch['queue'] = queue
    # console.rule('Updated batch block info')
    # console.print(spec.batch)

    study_name = spec.name



    # Run in foreground to enable easier checking of successful studies
    print(f"Running maestro study in '{tmp_outdir}'")
    
    maestro_cmd = ["maestro",
                   # "-d",
                   # "1",
                   "run",
                   "-s",
                   "1",
                   # "-t 1",
                   "-fg",
                   "-o",
                   tmp_outdir,
                   "--autoyes",
                   tmp_spec_path]

    # Check actual instance level
    try:
        current_instance_level = int(run(['flux', 'getattr', 'instance-level'],
                                         capture_output=True,
                                         encoding="utf-8").stdout)
    except Exception as ex:
        log.exception("Error querying instance level from flux")
        current_instance_level = -1  # Should we fail the test instead?
    
    if test_instance_level > 0 and current_instance_level < 1:
        # Assume default queue is fine for now
        maestro_cmd = ['flux', 'alloc', '-N', '1', '-t', '5m'] + maestro_cmd

    # time.sleep(20)
    spec_results = run(maestro_cmd,
                       capture_output=True,
                       cwd=tmp_path,
                       encoding="utf-8")


    testlog = tmp_path / (study_name + '_fg.log')
    try:
        # console.rule("Maestro Run: stdout")
        # console.print(spec_results.stdout)
        # console.rule("Maestro Run: stderr")
        # console.print(spec_results.stderr)
        with open(testlog, 'w') as testlog_file:
            
            log.warn(f"Test artifact saved at {testlog_file}")
            testlog_file.write(spec_results.stdout)
            testlog_file.write(spec_results.stderr)
    except FileNotFoundError as FNFE:
        log.exception(f"Error opening test log at '{testlog.resolve()}'")

    # Rename: conductor status
    # Add status.csv scraper for study state
    # Add warning/error scraper for the log
    completed_successfully = check_study_success(
        spec_results.stderr.split('\n'),
        study_name
    )

    # NOTE: running with -s to pytest for real time output fails with these as the
    # logger in maestro injects the ascii/cat codes for colors which breaks the log scraping
    # TODO: revisit when conductor/maestro patched to also write the log file
    #       when running in foreground and scrape that
    assert completed_successfully == expected_conductor_state
    spec_retcode = spec_results.returncode
    expected_retcode_str = retcode_predicate.__name__.replace('_', ' ').capitalize()
    assert retcode_predicate(spec_retcode), f"Expected '{expected_retcode_str}', got '{spec_retcode}'"

    # Before scraping status.csv we need to be sure we can see the outputs,
    # accounting for networked filesystem lag.  If logs show an error we shouldn't
    # get here anyway, but need a timeout to ensure we don't wait forever
    
    # Wait for the study workspace/status files, accounting for network lag
    fs_timeout = 60             # seconds
    poll_interval = 3           # seconds

    end_time = time.time() + fs_timeout
    status_file_exists = False
    status_file = tmp_outdir / 'status.csv'
    status_file = status_file.resolve()
    study_dir = tmp_outdir.resolve()
    while time.time() < end_time:
        console.print(f"{datetime.now()}: {study_dir} exists: {study_dir.exists()}")
        console.print(f"{datetime.now()}: {status_file} exists: {status_file.exists()}")
        if study_dir.exists() and status_file.exists():
            status_file_exists = True
            break

        time.sleep(poll_interval)

    if not status_file_exists:
        pytest.fail(
            f"Test timed out looking for status file at '{status_file}'."            
        )

    console.rule(f"Walking study workspace: {tmp_outdir}")
    for file in tmp_outdir.iterdir():
        console.print(f"{file.resolve()}")

    # Check for steps having 'FINISHED' state to catch job submission errors
    steps_finished = check_all_steps_finished(tmp_outdir)
    assert steps_finished == expected_step_finished

    # # Cleanup if successful
    # if os.path.exists(tmp_outdir):
    #     rmtree(tmp_outdir, ignore_errors=True)  # recursively delete workspace
