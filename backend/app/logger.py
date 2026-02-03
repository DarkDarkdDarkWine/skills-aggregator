from collections import deque
from datetime import datetime
import logging
import threading

log_buffer = deque(maxlen=1000)
log_buffer_lock = threading.Lock()


class LogCapture(logging.Handler):
    def emit(self, record: logging.LogRecord):
        if record.levelno >= logging.ERROR:
            with log_buffer_lock:
                log_buffer.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                        "exc_info": self.format(record) if record.exc_info else None,
                    }
                )


def setup_logging():
    log_handler = LogCapture()
    logging.getLogger().addHandler(log_handler)
