import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict


class ClinicalLogFormatter(logging.Formatter):
    """
    JSON log formatter designed for clinical system auditability and compliance.
    Ensures structured output with ISO-8601 UTC timestamps.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "request_id"):
            log_entry["request_id"] = getattr(record, "request_id")
        if hasattr(record, "audit"):
            log_entry["audit"] = getattr(record, "audit")
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_clinical_logger(name: str = "clinical_platform") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ClinicalLogFormatter())
        logger.addHandler(handler)

    logger.propagate = False
    return logger


logger = setup_clinical_logger()
