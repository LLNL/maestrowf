import os
from shutil import rmtree
from subprocess import run
# import tempfile

import pytest

from maestrowf.specification.yamlspecification import YAMLSpecification


# Tag every test in this file as requiring flux
pytestmark = [pytest.mark.sched_slurm,
              pytest.mark.integration,]


@pytest.mark.parametrize(
    "spec_name, tmp_dir",
    [
        ("hello_bye_parameterized_slurm.yaml", "HELLO_BYE_SLURM"),
    ]
)
def test_hello_world_slurm(samples_spec_path,
                           check_study_success,
                           spec_name,
                           tmp_dir):
    """
    Run integration tests using the slurm scheduler.
    """
    spec_path = samples_spec_path(spec_name)
    # TEMP dir run tests always trigger failure when running on flux machine?
    # tmp_outdir = tempfile.mkdtemp()

    tmp_outdir = os.path.abspath(os.path.join(os.getcwd(), tmp_dir))

    # Clean up detritus from failed tests
    if os.path.exists(tmp_outdir):
        rmtree(tmp_outdir, ignore_errors=True)  # recursively delete workspace

    spec = YAMLSpecification.load_specification(spec_path)
    study_name = spec.name

    # Run in foreground to enable easier checking of successful studies
    spec_results = run(["maestro",
                        "run",
                        "-s 1",
                        "-fg",
                        "-o",
                        tmp_outdir,
                        "--autoyes",
                        spec_path],
                       capture_output=True,
                       encoding="utf-8")

    with open(os.path.join(tmp_dir, 'logs', study_name + '_fg.log'), 'w') as testlog:
        testlog.write(spec_results.stdout)
        testlog.write(spec_results.stderr)

    completed_successfully = check_study_success(
        spec_results.stderr.split('\n'),
        study_name
    )

    assert completed_successfully
    assert spec_results.returncode == 0

    # Cleanup if successful
    if os.path.exists(tmp_outdir):
        rmtree(tmp_outdir, ignore_errors=True)  # recursively delete workspace
