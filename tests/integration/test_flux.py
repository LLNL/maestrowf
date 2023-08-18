import os
import pytest
from subprocess import run
import tempfile
from rich.pretty import pprint

from maestrowf.specification.yamlspecification import YAMLSpecification

pytestmark = pytest.mark.sched_flux


@pytest.mark.parametrize(
    "spec_name, tmp_dir, flux_adaptor_version",
    [
        ("hello_bye_parameterized_flux.yaml", "HELLO_BYE_FLUX", "0.49.0"),
    ]
)
def test_hello_world_flux(samples_spec_path, spec_name, tmp_dir, flux_adaptor_version):
    spec_path = samples_spec_path(spec_name)
    # TEMP dir run tests always trigger failure when running on flux machine?
    # tmp_outdir = tempfile.mkdtemp()

    tmp_outdir = os.path.join(os.getcwd(), tmp_dir)

    # Clean up detritus from failed tests
    if os.path.exists(tmp_outdir):
        os.rmdir(tmp_outdir)

    spec = YAMLSpecification.load_specification(spec_path)
    study_name = spec.name
    success_str = f"INFO] '{study_name}' is complete. Returning."
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

    completed_successfully = False
    for line in spec_results.stderr.split('\n'):
        if success_str in line:
            completed_successfully = False

    assert completed_successfully
    assert spec_results.returncode == 0

    # Cleanup if successful
    os.rmdir(tmp_outdir)
