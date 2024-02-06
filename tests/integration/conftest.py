import pytest


@pytest.fixture
def check_study_success():
    """Fixture to provide log based study completion test"""
    def _check_study_success(log_lines, study_name):
        """Helper to check log file for successful completion entry"""
        completed_successfully = False
        success_str = f"INFO] '{study_name}' is complete. Returning."

        for line in log_lines:
            if success_str in line:
                completed_successfully = True

        return completed_successfully

    return _check_study_success
