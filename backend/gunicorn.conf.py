"""Gunicorn settings for production. Override any of them with GUNICORN_* environment variables."""

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.getenv("GUNICORN_WORKERS", min(4, multiprocessing.cpu_count() * 2 + 1)))
worker_class = "uvicorn_worker.UvicornWorker"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "60"))
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
# Trust X-Forwarded-* from the reverse proxy on the same host.
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
