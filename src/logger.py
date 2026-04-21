import logging
import os
from datetime import datetime, timezone

LOG_FILE = "./logs/pipeline.log"

_logger = logging.getLogger("pipeline")
_logger.setLevel(logging.DEBUG)

_formatter = logging.Formatter("%(message)s")

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(_formatter)
_logger.addHandler(_console_handler)

try:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    _file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _file_handler.setFormatter(_formatter)
    _logger.addHandler(_file_handler)
except OSError:
    pass


def _format(status: str, filename: str, detail: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"[{ts}] [{status}] {filename} \u2014 {detail}"


def log_ok(filename: str, detail: str) -> None:
    _logger.info(_format("OK", filename, detail))


def log_skipped(filename: str, detail: str) -> None:
    _logger.info(_format("SKIPPED", filename, detail))


def log_unresolved(filename: str, detail: str) -> None:
    _logger.warning(_format("UNRESOLVED", filename, detail))


def log_ambiguous(filename: str, detail: str) -> None:
    _logger.warning(_format("AMBIGUOUS", filename, detail))


def log_error(filename: str, detail: str) -> None:
    _logger.error(_format("ERROR", filename, detail))
