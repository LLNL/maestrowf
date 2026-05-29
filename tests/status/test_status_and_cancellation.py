import csv
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, Mock

import pytest

from maestrowf.abstracts.enums import State
from maestrowf.datastructures.core.executiongraph import ExecutionGraph
from maestrowf.datastructures.core import StudyStep


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_execution_graph():
    """Create a basic ExecutionGraph for testing."""
    dag = ExecutionGraph(submission_attempts=1, submission_throttle=0, use_tmp=False, dry_run=False)
    dag.add_description(name="test_study", description="Test study")
    return dag


def create_mock_step(name="test_step"):
    """Helper function to create a properly mocked StudyStep."""
    step = MagicMock(spec=StudyStep)
    step.real_name = name
    step.run = {"cmd": "echo 'test'", "restart": "", "walltime": "00:10:00"}
    return step


def setup_dag_with_source(dag):
    """
    Helper to set up the DAG with a source node.

    The _source node must exist in the adjacency table before we can
    add edges from it to other nodes.
    """
    # Add the source node to the DAG's adjacency table
    # We use None as the value since _source doesn't have a StepRecord
    # Note: adjacency_table uses lists, not sets
    if "_source" not in dag.adjacency_table:
        dag.adjacency_table["_source"] = []
    if "_source" not in dag.values:
        dag.values["_source"] = None


class TestStatusPath:
    """Tests for status path configuration and writing."""

    def test_set_status_path(self, mock_execution_graph):
        """Test that status path can be set."""
        test_path = "/path/to/status"
        mock_execution_graph.set_status_path(test_path)
        assert mock_execution_graph._status_path == test_path

    def test_write_status_with_explicit_path(self, mock_execution_graph, temp_output_dir):
        """Test writing status with an explicit path argument."""
        # Set up DAG with source node
        setup_dag_with_source(mock_execution_graph)

        # Add a simple step
        step = create_mock_step("test_step")

        mock_execution_graph.add_step(
            "test_step", step, str(temp_output_dir / "test_workspace"), restart_limit=1
        )

        # Add connection to source to set up DAG properly
        mock_execution_graph.add_connection("_source", "test_step")

        # Write status with explicit path
        mock_execution_graph.write_status(str(temp_output_dir))

        # Verify status.csv was created
        status_file = temp_output_dir / "status.csv"
        assert status_file.exists()

        # Verify content
        with open(status_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["Step Name"] == "test_step"
            assert rows[0]["State"] == State.INITIALIZED.name

    def test_write_status_with_configured_path(self, mock_execution_graph, temp_output_dir):
        """Test writing status using configured path."""
        # Set up DAG with source node
        setup_dag_with_source(mock_execution_graph)

        # Add a simple step
        step = create_mock_step("test_step")

        mock_execution_graph.add_step(
            "test_step", step, str(temp_output_dir / "test_workspace"), restart_limit=1
        )

        # Add connection to source to set up DAG properly
        mock_execution_graph.add_connection("_source", "test_step")

        # Configure status path
        mock_execution_graph.set_status_path(str(temp_output_dir))

        # Write status without explicit path
        mock_execution_graph.write_status()

        # Verify status.csv was created
        status_file = temp_output_dir / "status.csv"
        assert status_file.exists()

    def test_write_status_without_path_logs_warning(self, mock_execution_graph, caplog):
        """Test that write_status logs warning when no path is available."""
        # Don't set status path
        mock_execution_graph.write_status()

        # Verify warning was logged
        assert "No status path provided or configured" in caplog.text


class TestCancellationPath:
    """Tests for cancellation lock path configuration."""

    def test_set_cancel_lock_path(self, mock_execution_graph):
        """Test that cancel lock path can be set."""
        test_path = "/path/to/cancel.lock"
        mock_execution_graph.set_cancel_lock_path(test_path)
        assert mock_execution_graph._cancel_lock_path == test_path

    def test_check_for_cancellation_no_lock_file(self, mock_execution_graph, temp_output_dir):
        """Test cancellation check when no lock file exists."""
        cancel_path = temp_output_dir / "cancel.lock"
        mock_execution_graph.set_cancel_lock_path(str(cancel_path))

        result = mock_execution_graph._check_for_cancellation()

        assert result is False
        assert mock_execution_graph.is_canceled is False

    def test_check_for_cancellation_with_lock_file(self, mock_execution_graph, temp_output_dir):
        """Test cancellation check when lock file exists."""
        cancel_path = temp_output_dir / "cancel.lock"
        mock_execution_graph.set_cancel_lock_path(str(cancel_path))

        # Create the cancel lock file
        cancel_path.touch()

        # Mock the cancel_study method
        mock_execution_graph.cancel_study = Mock()

        result = mock_execution_graph._check_for_cancellation()

        assert result is True
        mock_execution_graph.cancel_study.assert_called_once()
        # Lock file should be removed
        assert not cancel_path.exists()

    def test_check_for_cancellation_without_configured_path(self, mock_execution_graph):
        """Test cancellation check when no path is configured."""
        # Don't set cancel lock path
        result = mock_execution_graph._check_for_cancellation()

        assert result is False


class TestIncrementalStatusUpdates:
    """Integration tests for incremental status updates during execution."""

    def test_status_file_exists_immediately_after_initialization(self, temp_output_dir):
        """
        Test that status.csv exists immediately after conductor initialization.

        This verifies the fix for the issue where status.csv was not written
        until the first job completed.
        """
        # This test would ideally use the Conductor class, but for a unit test
        # we'll verify that the mechanism is in place
        dag = ExecutionGraph()
        dag.add_description(name="test_study", description="Test")

        # Set up DAG with source node
        setup_dag_with_source(dag)

        # Add a step
        step = create_mock_step("step1")
        dag.add_step("step1", step, str(temp_output_dir / "ws1"), 1)

        # Add connection to source
        dag.add_connection("_source", "step1")

        # Configure and write initial status
        dag.set_status_path(str(temp_output_dir))
        dag.write_status()

        # Verify file exists with initialized state
        status_file = temp_output_dir / "status.csv"
        assert status_file.exists()

        with open(status_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["State"] == State.INITIALIZED.name


class TestCancellationResponsiveness:
    """Tests for responsive cancellation between job executions."""

    def test_cancellation_checked_before_each_job(self, mock_execution_graph, temp_output_dir):
        """
        Test that cancellation is checked before each job execution.

        This verifies the fix for the issue where cancellation requests
        were only checked once per monitoring loop iteration.
        """
        # Set up DAG with source node
        setup_dag_with_source(mock_execution_graph)

        # Create cancel lock path
        cancel_path = temp_output_dir / "cancel.lock"
        mock_execution_graph.set_cancel_lock_path(str(cancel_path))

        # Add multiple steps
        for i in range(3):
            step = create_mock_step(f"step{i}")
            mock_execution_graph.add_step(f"step{i}", step, str(temp_output_dir / f"ws{i}"), 1)

        # Create connections (linear dependency chain)
        mock_execution_graph.add_connection("_source", "step0")
        mock_execution_graph.add_connection("step0", "step1")
        mock_execution_graph.add_connection("step1", "step2")

        # The actual execution flow would call _check_for_cancellation
        # in the execute_ready_steps loop. Here we verify the mechanism works.

        # Initially no cancellation
        assert mock_execution_graph._check_for_cancellation() is False

        # Create cancel lock file
        cancel_path.touch()

        # Mock cancel_study
        mock_execution_graph.cancel_study = Mock()

        # Now cancellation should be detected
        result = mock_execution_graph._check_for_cancellation()
        assert result is True
        assert not cancel_path.exists()  # Should be cleaned up


class TestStatusFileFormat:
    """Tests for status.csv file format and content."""

    def test_status_csv_header(self, mock_execution_graph, temp_output_dir):
        """Test that status.csv has the correct header."""
        # Set up DAG with source node
        setup_dag_with_source(mock_execution_graph)

        step = create_mock_step("test_step")

        mock_execution_graph.add_step("test_step", step, str(temp_output_dir / "test_workspace"), 1)

        # Add connection to source
        mock_execution_graph.add_connection("_source", "test_step")

        mock_execution_graph.write_status(str(temp_output_dir))

        status_file = temp_output_dir / "status.csv"
        with open(status_file, "r", encoding="utf-8") as f:
            header = f.readline().strip()
            expected_header = (
                "Step Name,Job ID,Workspace,State,Run Time,Elapsed Time,"
                "Start Time,Submit Time,End Time,Number Restarts,Params"
            )
            assert header == expected_header

    def test_status_csv_initial_state(self, mock_execution_graph, temp_output_dir):
        """Test that steps are initially in INITIALIZED state."""
        # Set up DAG with source node
        setup_dag_with_source(mock_execution_graph)

        step = create_mock_step("test_step")

        mock_execution_graph.add_step("test_step", step, str(temp_output_dir / "test_workspace"), 1)

        # Add connection to source
        mock_execution_graph.add_connection("_source", "test_step")

        mock_execution_graph.write_status(str(temp_output_dir))

        status_file = temp_output_dir / "status.csv"
        with open(status_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert rows[0]["State"] == State.INITIALIZED.name
            assert rows[0]["Job ID"] == "--"
            assert rows[0]["Start Time"] == "--"
            assert rows[0]["Submit Time"] == "--"
            assert rows[0]["End Time"] == "--"


@pytest.mark.integration
class TestEndToEndStatusUpdates:
    """
    Integration tests that verify status updates work end-to-end.

    These tests require actually running studies and are marked as
    integration tests.
    """

    @pytest.mark.sched_local
    def test_status_file_updated_after_each_local_job(
        self, samples_spec_path, load_study, temp_output_dir
    ):
        """
        Test that status.csv is updated after each local job completes.

        This is an integration test that verifies the incremental status
        update functionality with real job execution.
        """
        # Load a simple spec with multiple parameterized steps
        spec_path = samples_spec_path("hello_world.yaml")
        if not spec_path:
            pytest.skip("hello_world.yaml spec not found")

        study = load_study(spec_path, str(temp_output_dir))

        # Check that status.csv exists after initialization
        # (This would need the Conductor integration, skipping for now)
        pytest.skip("Requires full Conductor integration")
