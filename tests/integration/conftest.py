import pytest

from maestrowf.abstracts.enums import State
from maestrowf.conductor import Conductor


@pytest.fixture
def check_study_success():
    """Fixture to provide log based study completion test"""
    # NOTE: may want to rename this as 'conductor status' since it can
    # finish even if the study failed
    def _check_study_success(log_lines, study_name):
        """Helper to check log file for successful completion entry"""
        completed_successfully = False
        success_str = f"INFO] '{study_name}' is complete. Returning."

        for line in log_lines:
            if success_str in line:
                completed_successfully = True

        return completed_successfully

    return _check_study_success


@pytest.fixture
def check_study_warnings():
    """Fixture to provide check for warnings in the study log"""
    def _check_study_warnings(log_lines):
        """Helper to check log file for presence of warnings like 'job failure reported'"""
        warnings_found = False
        warning_str = "WARNING"
        log_setup_str = "setup_logging"  # ignore WARNING marker here

        for line in log_lines:
            if warning_str in line and log_setup_str not in line:
                warnings_found = True

        return warnings_found

    return _check_study_warnings


@pytest.fixture
def check_study_errors():
    """Fixture to provide check for presence of errors in the study log"""
    def _check_study_errors(log_lines):
        """Helper to check log file for presence of errors"""
        errors_found = False
        error_str = "ERROR"
        log_setup_str = "setup_logging"  # ignore ERROR marker here

        for line in log_lines:
            if error_str in line and log_setup_str not in line:
                errors_found = True

        return errors_found

    return _check_study_errors


@pytest.fixture
def check_all_steps_finished():
    """Fixture to test that all steps in a study have the FINISHED state"""
    # NOTE: are all steps always there, or are some delayed as with workspaces?
    def _check_all_steps_finished(study_output_dir):
        """Helper to check status.csv to verify all steps have 'finished' state"""
        # NOTE: can this be empty?
        step_status = Conductor.get_status(study_output_dir)
        print(step_status)

        # Catch error case where status might be empty
        if 'State' not in step_status or not step_status['State']:
            return False
        
        return all(state == State.FINISHED.name for state in step_status['State'])

    return _check_all_steps_finished
