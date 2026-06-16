import logging
import os
import tempfile

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
