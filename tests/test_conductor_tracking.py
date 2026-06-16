import logging

import pytest

import maestrowf.conductor as conductor_module
from maestrowf.abstracts.enums import StudyStatus
from maestrowf.conductor import Conductor
from maestrowf.utils import atomic_write_file


class DummyStudy:
    name = "dummy_study"

    def __init__(self, output_path):
        self.output_path = str(output_path)


class FinishingDag:
    name = "dummy_study"

    def execute_ready_steps(self):
        return StudyStatus.FINISHED

    def pickle(self, path):
        pass

    def write_status(self, path):
        pass


class FailingDag:
    name = "dummy_study"

    def execute_ready_steps(self):
        raise RuntimeError("boom")


class RunningThenFailingDag:
    name = "dummy_study"

    def __init__(self):
        self._calls = 0

    def execute_ready_steps(self):
        self._calls += 1
        if self._calls == 1:
            return StudyStatus.RUNNING
        raise RuntimeError("boom")

    def pickle(self, path):
        pass

    def write_status(self, path):
        pass


def test_conductor_registration_creates_process_record(tmp_path):
    conductor = Conductor(DummyStudy(tmp_path))

    conductor_id = conductor.register_conductor()
    conductors = Conductor.get_conductors(tmp_path)

    assert conductor_id in conductors
    record = conductors[conductor_id]
    assert record["conductor_id"] == conductor_id
    assert record["study_name"] == "dummy_study"
    assert record["output_path"] == str(tmp_path)
    assert record["pid"]
    assert record["hostname"]
    assert record["argv"]
    assert record["conductor_argv"]
    assert record["conductor_executable"]
    assert record["conductor_command"]
    assert record["conductor_mode"] == "standalone"
    assert record["conductor_status"] == "running"
    assert record["conductor_started_at"]
    assert record["conductor_last_heartbeat_at"] == \
        record["conductor_started_at"]
    assert record["conductor_ended_at"] is None
    assert record["last_observed_study_status"] is None
    assert record["final_study_status"] is None
    record_path = tmp_path / "logs" / ".conductors" / \
        "{}.json".format(conductor_id)
    assert record_path.exists()


def test_foreground_conductor_records_mode(tmp_path):
    conductor = Conductor(DummyStudy(tmp_path), conductor_mode="foreground")

    conductor_id = conductor.register_conductor()
    record = Conductor.get_conductors(tmp_path)[conductor_id]

    assert record["conductor_mode"] == "foreground"


def test_conductor_heartbeat_updates_record(tmp_path):
    conductor = Conductor(DummyStudy(tmp_path))
    conductor_id = conductor.register_conductor()
    original = Conductor.get_conductors(tmp_path)[conductor_id]

    conductor.heartbeat_conductor("checking work")
    updated = Conductor.get_conductors(tmp_path)[conductor_id]

    assert updated["conductor_started_at"] == \
        original["conductor_started_at"]
    assert updated["conductor_status_message"] == "checking work"
    assert updated["conductor_last_heartbeat_at"] >= \
        original["conductor_last_heartbeat_at"]
    assert updated["conductor_status"] == "running"


def test_conductor_finish_marks_record_completed(tmp_path):
    conductor = Conductor(DummyStudy(tmp_path))
    conductor_id = conductor.register_conductor()

    conductor.finish_conductor(
        "completed", StudyStatus.FINISHED, "study finished")
    record = Conductor.get_conductors(tmp_path)[conductor_id]

    assert record["conductor_status"] == "completed"
    assert record["final_study_status"] == StudyStatus.FINISHED.name
    assert record["last_observed_study_status"] == StudyStatus.FINISHED.name
    assert record["conductor_status_message"] == "study finished"
    assert record["conductor_ended_at"]


def test_multiple_conductor_records_can_coexist(tmp_path):
    conductor_a = Conductor(DummyStudy(tmp_path))
    conductor_b = Conductor(DummyStudy(tmp_path))

    id_a = conductor_a.register_conductor()
    id_b = conductor_b.register_conductor()
    conductors = Conductor.get_conductors(tmp_path)

    assert id_a in conductors
    assert id_b in conductors
    assert id_a != id_b


def test_atomic_write_file_replaces_complete_file(tmp_path):
    path = tmp_path / "record.json"
    atomic_write_file(path, '{\n  "old": true\n}\n')

    atomic_write_file(path, '{\n  "new": true\n}\n')

    assert path.read_text() == '{\n  "new": true\n}\n'


def test_conductor_setup_logging_writes_start_divider(tmp_path):
    root_logger = conductor_module.ROOTLOGGER
    original_handlers = list(root_logger.handlers)

    conductor_module.setup_logging("dummy_study", str(tmp_path), log_lvl=2)

    for handler in list(root_logger.handlers):
        if handler not in original_handlers:
            handler.flush()
            root_logger.removeHandler(handler)
            handler.close()

    contents = (tmp_path / "logs" / "dummy_study.log").read_text()
    assert "Running Maestro Conductor standalone." in contents
    assert "Conductor log file:" in contents


def test_monitor_marks_record_completed(tmp_path):
    conductor = Conductor(DummyStudy(tmp_path))
    conductor._setup = True
    conductor._pkl_path = str(tmp_path)
    conductor._exec_dag = FinishingDag()
    conductor.sleep_time = 1
    conductor_id = conductor.register_conductor()

    assert conductor.monitor_study() == StudyStatus.FINISHED
    record = Conductor.get_conductors(tmp_path)[conductor_id]
    assert record["conductor_status"] == "completed"
    assert record["final_study_status"] == StudyStatus.FINISHED.name
    assert record["last_observed_study_status"] == StudyStatus.FINISHED.name


def test_monitor_marks_record_failed_on_exception(tmp_path):
    conductor = Conductor(DummyStudy(tmp_path))
    conductor._setup = True
    conductor._pkl_path = str(tmp_path)
    conductor._exec_dag = FailingDag()
    conductor.sleep_time = 1
    conductor_id = conductor.register_conductor()

    with pytest.raises(RuntimeError):
        conductor.monitor_study()

    record = Conductor.get_conductors(tmp_path)[conductor_id]
    assert record["conductor_status"] == "failed"
    assert record["final_study_status"] is None
    assert record["conductor_status_message"] == \
        "monitoring failed with an exception"


def test_monitor_preserves_last_observed_status_on_exception(tmp_path):
    conductor = Conductor(DummyStudy(tmp_path))
    conductor._setup = True
    conductor._pkl_path = str(tmp_path)
    conductor._exec_dag = RunningThenFailingDag()
    conductor.sleep_time = 0
    conductor_id = conductor.register_conductor()

    with pytest.raises(RuntimeError):
        conductor.monitor_study()

    record = Conductor.get_conductors(tmp_path)[conductor_id]
    assert record["conductor_status"] == "failed"
    assert record["last_observed_study_status"] == StudyStatus.RUNNING.name
    assert record["final_study_status"] is None


def test_conductor_record_update_failures_do_not_raise(
        tmp_path, monkeypatch, caplog):
    conductor = Conductor(DummyStudy(tmp_path))

    def fail_update(*args, **kwargs):
        raise OSError("record unavailable")

    monkeypatch.setattr(Conductor, "_update_conductor_record", fail_update)
    caplog.set_level(logging.WARNING)

    conductor.register_conductor()
    conductor.heartbeat_conductor("checking work")
    conductor.observe_study_status(StudyStatus.RUNNING)
    conductor.finish_conductor("failed", None, "cleanup failed")

    assert "Unable to register conductor record" in caplog.text
    assert "Unable to heartbeat conductor record" in caplog.text
    assert "Unable to update observed study status conductor record" in \
        caplog.text
    assert "Unable to finish conductor record" in caplog.text
