from __future__ import annotations

import logging
import sys

_LOG_FORMAT = "[%(levelname)s] %(message)s"
_LOGGER_NAMESPACE = "newsletter"


class _MaxLevelFilter(logging.Filter):
    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


def configure_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger(_LOGGER_NAMESPACE)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(_MaxLevelFilter(logging.WARNING))
    stdout_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
