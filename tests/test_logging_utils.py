import logging

from backend.legacy import logging_utils
from backend.legacy import current_config


def test_setup_logger_respects_current_config_levels(tmp_path, monkeypatch):
    # Reset cached logger and point results to temp folder
    monkeypatch.setattr(logging_utils, "_CACHED_LOGGER", None)
    monkeypatch.setattr(current_config.current_config, "LOG_LEVEL_CONSOLE", "WARNING")
    monkeypatch.setattr(current_config.current_config, "LOG_LEVEL_FILE", "DEBUG")
    monkeypatch.setattr(current_config.current_config, "RESULT_FOLDER", tmp_path)

    logger = logging_utils.setup_logger(log_filename="test.log")

    # Emit something to ensure the file handler writes
    logger.info("info message to file")
    logger.warning("warning message to both")

    levels = {type(h): h.level for h in logger.handlers}
    assert levels.get(logging.StreamHandler) == logging.WARNING
    assert levels.get(logging.FileHandler) == logging.DEBUG

    log_file = tmp_path / "test.log"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "warning message to both" in content
