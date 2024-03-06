from collections import defaultdict
import os
from subprocess import check_output

import pytest

from maestrowf.utils import parse_version

from rich.pretty import pprint

SCHEDULERS = set(('sched_lsf', 'sched_slurm', 'sched_flux'))
SCHED_CHECKS = defaultdict(lambda: False)


def check_lsf():
    """
    Checks if there is an lsf instance to schedule to. NOT IMPLEMENTED YET.
    """
    return False


SCHED_CHECKS['sched_lsf'] = check_lsf


def check_slurm():
    """
    Checks if there is a slurm instance to schedule to. NOT IMPLEMENTED YET.
    """
    slurm_info_func = 'sinfo'
    try:
        slurm_ver_output_lines = check_output([slurm_info_func,'-V'], encoding='utf8')
    except FileNotFoundError as fnfe:
        if fnfe.filename == slurm_info_func:
            return False

        raise

    slurm_ver_parts = slurm_ver_output_lines.split('\n')[0].split()
    version = parse_version(slurm_ver_parts[1])

    if slurm_ver_parts[0].lower() == 'slurm' and version:
        return True

    return False


SCHED_CHECKS['sched_slurm'] = check_slurm


def check_flux():
    """
    Checks if there is a flux scheduler to schedule to.

    Returns
    -------
    True if flux bindings installed and active broker found, False if not
    """
    try:
        import flux

        fhandle = flux.Flux()

    except ImportError:
        # Flux bindings not found
        return False

    except FileNotFoundError:
        # Couldn't connect to a broker
        return False

    return True


SCHED_CHECKS['sched_flux'] = check_flux


def check_for_scheduler(sched_name):
    """
    Thin wrapper for dispatching scheduler presence testing for marking
    tests to be skipped
    """
    return SCHED_CHECKS[sched_name]()


def pytest_runtest_setup(item):
    """Helper for applying automated test marking"""
    # Scheduler dependent checks
    for marker in item.iter_markers():
        if not marker.name.startswith('sched_'):
            continue

        if marker.name not in SCHEDULERS:
            pytest.skip(f"'{marker}' is not a supported scheduler")

        if not check_for_scheduler(marker.name):
            pytest.skip(f"not currently running tests on '{marker}' managed system")


@pytest.fixture
def samples_spec_path():
    """
    Fixture for providing maestro specifications from the samples
    directories
    """
    def load_spec(file_name):
        samples_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'samples'
        )

        for dirpath, dirnames, filenames in os.walk(samples_dir):
            for fname in filenames:
                if file_name == fname:
                    return os.path.join(dirpath, file_name)

    return load_spec

from maestrowf.specification.yamlspecification import YAMLSpecification


@pytest.fixture
def spec_path():
    """
    Fixture for providing maestro specifications from test data directories
    """
    def load_spec(file_name):
        dirpath = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirpath, "specification", "test_specs", file_name)

    return load_spec


@pytest.fixture
def spec(spec_path):
    def load_spec(file_name):
        spec = YAMLSpecification.load_specification(spec_path(file_name))
        return spec
    return load_spec

@pytest.fixture
def study_steps(spec):
    def load_study_steps(spec_file_name):
        study_spec = spec(spec_file_name)

        steps = study_spec.get_study_steps()

        return steps

    return load_study_steps

@pytest.fixture
def status_csv_path():
    """Fixture for providing status files from test data directories"""
    def load_status_csv(file_name):
        dirpath = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirpath, "status", "test_status_data", file_name)

    return load_status_csv


from maestrowf.datastructures.core.study import Study

@pytest.fixture
def study_obj(spec, tmp_path):
    """Fixture for providing Study objects"""

    def load_study(spec_file_name):
        study_spec = spec(spec_file_name)
        pprint(f"Loaded spec {study_spec}")
        study_env = study_spec.get_study_environment()
        pprint(f"Found study environment {study_env}")
        study_params = study_spec.get_parameters()
        pprint(f"Found study parameters {study_params}")
        study_steps = study_spec.get_study_steps()
        pprint(f"Found study steps {study_steps}")
        output_path = tmp_path

        study = Study(study_spec.name, study_spec.description, studyenv=study_env,
                  parameters=study_params, steps=study_steps, out_path=output_path)
        return study

    return load_study
