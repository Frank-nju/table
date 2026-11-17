"""Background worker: delivers queued email and runs periodic jobs.

Run exactly one long-lived instance alongside the web server:

    python -m app.worker
"""

from __future__ import annotations

import logging
import signal
import threading

from app.config import get_settings
from app.db import SessionLocal
from app.services.jobs import run_all

log = logging.getLogger("app.worker")


def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    log.info("Worker started (interval %ss)", settings.scheduler_interval_seconds)
    while not stop.is_set():
        with SessionLocal() as db:
            results = run_all(db)
        if any(results.values()):
            log.info("Jobs: %s", results)
        stop.wait(settings.scheduler_interval_seconds)
    log.info("Worker stopped")


if __name__ == "__main__":
    main()
