import logging
import os
from typing import Optional

from backend.legacy.current_config import current_config


def _coerce_level(level, default=logging.INFO):
    if level is None:
        return default
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return logging._nameToLevel.get(level.upper(), default)
    return default


_CACHED_LOGGER = None


def setup_logger(
    name: str = "ea_agent",
    log_level: int = logging.INFO,
    console_level: Optional[int] = None,
    file_level: Optional[int] = None,
    log_filename: str = "run.log",
) -> logging.Logger:
    """
    Create (or return) a logger that writes to stdout and to a file under the current
    result folder. You can adjust verbosity independently per handler via console_level
    and file_level; per-message detail is controlled by using the logger at the desired
    level (logger.debug/info/warning/error/critical).
    """
    global _CACHED_LOGGER
    if _CACHED_LOGGER:
        return _CACHED_LOGGER

    # Pull defaults from current_config if explicit levels are not provided
    log_level = _coerce_level(log_level, logging.INFO)
    console_level = _coerce_level(
        console_level if console_level is not None else getattr(current_config, "LOG_LEVEL_CONSOLE", None),
        log_level,
    )
    file_level = _coerce_level(
        file_level if file_level is not None else getattr(current_config, "LOG_LEVEL_FILE", None),
        log_level,
    )

    logger = logging.getLogger(name)
    if logger.handlers:
        # Reconfigure if cached logger was reset (e.g. during tests) so handler levels
        # and destinations reflect current settings.
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    logger.setLevel(logging.DEBUG)  # allow handlers to filter

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(module)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler inside the configured result folder.
    result_folder = getattr(current_config, "RESULT_FOLDER", None)
    if result_folder:
        os.makedirs(result_folder, exist_ok=True)
        log_path = os.path.join(result_folder, log_filename)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(file_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.propagate = False
    _CACHED_LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    """
    Convenience accessor to retrieve the shared logger without needing to pass
    it around explicitly. Uses default levels/paths.
    """
    return setup_logger()
