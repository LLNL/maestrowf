import os
import pytest
from collections import defaultdict

SCHEDULERS = set(('sched_lsf', 'sched_slurm', 'sched_flux'))
SCHED_CHECKS = defaultdict(lambda: False)

def check_lsf():
    return False

SCHED_CHECKS['sched_lsf'] = check_lsf

def check_slurm():
    return False

SCHED_CHECKS['sched_slurm'] = check_slurm

def check_flux():
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
    return SCHED_CHECKS[sched_name]()


def pytest_runtest_setup(item):
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


@pytest.fixture
def spec_path():
    def load_spec(file_name):
        dirpath = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirpath, "specification", "test_specs", file_name)

    return load_spec


@pytest.fixture
def status_csv_path():
    def load_status_csv(file_name):
        dirpath = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(dirpath, "status", "test_status_data", file_name)

    return load_status_csv
