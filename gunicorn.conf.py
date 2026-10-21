
import os

DEFAULT_WORKERS = "2"
DEFAULT_THREADS = "4"
DEFAULT_TIMEOUT = "30"
GRACEFUL_TIMEOUT_SECONDS = 30
KEEPALIVE_SECONDS = 5
MAX_REQUESTS = 1000
MAX_REQUESTS_JITTER = 100

workers = int(os.environ.get("WEB_CONCURRENCY", DEFAULT_WORKERS))
threads = int(os.environ.get("GUNICORN_THREADS", DEFAULT_THREADS))
worker_class = "gthread"

timeout = int(os.environ.get("GUNICORN_TIMEOUT", DEFAULT_TIMEOUT))
graceful_timeout = GRACEFUL_TIMEOUT_SECONDS
keepalive = KEEPALIVE_SECONDS

max_requests = MAX_REQUESTS
max_requests_jitter = MAX_REQUESTS_JITTER

accesslog = "-"
errorlog = "-"
