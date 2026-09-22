"""Production Structured JSON Logger with Daily Rotation and Performance Telemetry."""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Formats logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(
    log_dir: str = "logs",
    log_level: str = "INFO",
    enable_console: bool = True
) -> logging.Logger:
    """
    Initialize FO-X 5M application logger.
    """

    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("fox_engine")
    logger.setLevel(
        getattr(logging, log_level.upper(), logging.INFO)
    )

    logger.handlers.clear()

    formatter = JSONFormatter()

    if enable_console:
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        logger.addHandler(console)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    file_handler = logging.FileHandler(
        os.path.join(log_dir, f"fox_engine_{today}.log"),
        encoding="utf-8"
    )

    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Global application logger
app_logger = setup_logger()


def log_event(
    event_name: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    level: str = "INFO",
    event_type: Optional[str] = None,
    message: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
):
    """
    Structured application event logger.

    Supports both event_name and event_type
    for backward compatibility.
    """

    # Older callers passed (event_name, message, payload) positionally.
    if isinstance(level, dict):
        data = level
        level = "INFO"
    if isinstance(data, str):
        data = payload
    elif payload is not None:
        data = payload
    if message is not None and data is None:
        data = {"message": message}
    event = event_type or event_name or "UNKNOWN_EVENT"

    logger = logging.getLogger("fox_engine")

    extra = {
        "extra_data": {
            "event_type": event,
            "data": data or {},
        }
    }

    logger.log(
        getattr(logging, level.upper(), logging.INFO),
        f"Event: {event}",
        extra=extra,
    )
    """
    Structured event logging helper.
    """

    extra = {
        "event": event_name,
        "extra_data": data or {}
    }

    getattr(
        app_logger,
        level.lower(),
        app_logger.info
    )(
        event_name,
        extra=extra
    )


class ExecutionTimer:
    """Measures execution latency."""

    def __init__(
        self,
        operation_name: str,
        logger: Optional[logging.Logger] = None,
        threshold_ms: float = 10.0
    ):
        self.operation = operation_name
        self.logger = logger or app_logger
        self.threshold_ms = threshold_ms
        self.start_time = 0.0


    def __enter__(self):
        self.start_time = time.perf_counter()
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):

        elapsed_ms = (
            time.perf_counter() - self.start_time
        ) * 1000

        if elapsed_ms > self.threshold_ms:

            self.logger.warning(
                f"{self.operation} slow execution",
                extra={
                    "extra_data": {
                        "latency_ms": round(elapsed_ms, 2),
                        "operation": self.operation
                    }
                }
            )