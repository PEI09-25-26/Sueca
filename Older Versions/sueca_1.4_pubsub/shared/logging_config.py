import logging
import uuid
import os
import json
import contextvars

# Context var to store correlation id for the current context/thread
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar('correlation_id', default='-')


class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        # Read correlation id from contextvar
        try:
            cid = correlation_id_ctx.get()
        except Exception:
            cid = '-'
        record.correlation_id = cid or '-'
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', '-')
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging(level: str = None):
    level = level or os.getenv('LOG_LEVEL', 'INFO')
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(CorrelationIdFilter())

    # Remove default handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    root.addHandler(handler)


def correlation_id_from_request(request):
    # Look for incoming correlation header or generate new
    hdr = request.headers.get('X-Correlation-ID')
    if hdr:
        return hdr
    return str(uuid.uuid4())


def set_correlation_id(cid: str):
    try:
        correlation_id_ctx.set(cid or '-')
    except Exception:
        pass


def clear_correlation_id():
    try:
        correlation_id_ctx.set('-')
    except Exception:
        pass
