import logging
import os
import tempfile
from argparse import Namespace

from maestrowf import maestro


def test_staged_log_handler_uses_temp_file_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    staged_path, handler = maestro.create_staged_log_handler(2)

    try:
        assert os.path.dirname(staged_path) == tempfile.gettempdir()
        assert os.path.dirname(staged_path) != str(tmp_path)
        assert os.path.basename(staged_path).startswith("maestro-setup-")

        maestro.log_to_handler(
            handler, logging.INFO, "setup logging before output path")
        handler.flush()

        contents = open(staged_path, "r").read()
        assert "===== maestro run setup logging started =====" in contents
        assert "Temporary setup log path: {}".format(staged_path) in contents
    finally:
        maestro.cleanup_staged_log(staged_path, handler)

    assert not os.path.exists(staged_path)


def test_promote_staged_log_marks_study_log(tmp_path):
    staged_path, staged_handler = maestro.create_staged_log_handler(2)
    study_log = tmp_path / "logs" / "study.log"
    final_handler = None

    try:
        maestro.log_to_handler(
            staged_handler, logging.INFO, "setup logging before promotion")

        final_handler = maestro.promote_staged_log(
            staged_path, staged_handler, str(study_log), 2)

        final_handler.flush()
        contents = study_log.read_text()
        assert "setup logging before promotion" in contents
        assert "===== maestro run setup logging promoted to study log =====" \
            in contents
        assert "Removed temporary setup log file after promotion: {}".format(
            staged_path) in contents
        assert not os.path.exists(staged_path)
    finally:
        maestro.close_log_handler(final_handler)
        maestro.cleanup_staged_log(staged_path, staged_handler)


class FakeEnvironment:
    def remove(self, name):
        return None

    def add(self, variable):
        pass


class FakeSpecification:
    name = "fake_study"
    description = "fake study"
    batch = None

    def get_study_environment(self):
        return FakeEnvironment()

    def get_study_steps(self):
        return []

    def get_parameters(self):
        return {}


class FakeStudy:
    def __init__(self, name, description, studyenv=None, parameters=None,
                 steps=None, out_path=None):
        self.name = name
        self.output_path = out_path

    def setup_workspace(self):
        os.makedirs(self.output_path, exist_ok=True)

    def configure_study(self, **kwargs):
        pass

    def setup_environment(self):
        pass


def test_run_study_removes_promoted_log_handler_when_returning(
        tmp_path, monkeypatch):
    spec_path = tmp_path / "study.yaml"
    spec_path.write_text("description: fake\n")
    output_path = tmp_path / "output"

    monkeypatch.setattr(
        maestro.YAMLSpecification, "load_specification",
        lambda path: FakeSpecification())
    monkeypatch.setattr(maestro, "Study", FakeStudy)
    monkeypatch.setattr(maestro.Conductor, "store_study", lambda study: None)

    args = Namespace(
        debug_lvl=2,
        specification=str(spec_path),
        out=str(output_path),
        autoyes=False,
        autono=True,
        pargs=[],
        pgen=None,
        attempts=1,
        throttle=0,
        rlimit=1,
        usetmp=False,
        hashws=False,
        dry=False,
        sleeptime=1,
        fg=False,
    )

    assert maestro.run_study(args) == 0

    study_log = output_path / "logs" / "fake_study.log"
    logging.getLogger().warning("record after run_study returned")

    assert "record after run_study returned" not in study_log.read_text()


def test_run_study_background_launch_uses_standalone_conductor(
        tmp_path, monkeypatch):
    spec_path = tmp_path / "study.yaml"
    spec_path.write_text("description: fake\n")
    output_path = tmp_path / "output"
    commands = []

    monkeypatch.setattr(
        maestro.YAMLSpecification, "load_specification",
        lambda path: FakeSpecification())
    monkeypatch.setattr(maestro, "Study", FakeStudy)
    monkeypatch.setattr(maestro.Conductor, "store_study", lambda study: None)
    monkeypatch.setattr(maestro, "start_process", commands.append)

    args = Namespace(
        debug_lvl=2,
        specification=str(spec_path),
        out=str(output_path),
        autoyes=True,
        autono=False,
        pargs=[],
        pgen=None,
        attempts=1,
        throttle=0,
        rlimit=1,
        usetmp=False,
        hashws=False,
        dry=False,
        sleeptime=1,
        fg=False,
    )

    assert maestro.run_study(args) == 0

    assert len(commands) == 1
    assert "--launch-mode" not in commands[0]
    assert "nohup conductor" in commands[0]
