import logging
import json
import sys
from datetime import datetime
from typing import Any

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "name": record.name
        }
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger("sponsorship")
    logger.setLevel(logging.INFO)
    
    # Console Handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    # Specialized loggers
    auth_logger = logging.getLogger("sponsorship.auth")
    payment_logger = logging.getLogger("sponsorship.payment")
    security_logger = logging.getLogger("sponsorship.security")
    
    return logger

logger = setup_logging()
auth_logger = logging.getLogger("sponsorship.auth")
payment_logger = logging.getLogger("sponsorship.payment")
security_logger = logging.getLogger("sponsorship.security")
