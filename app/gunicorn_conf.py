"""Gunicorn hooks for Prometheus multiprocess metrics (`gunicorn -c python:app.gunicorn_conf`)."""

import os
import shutil
from typing import Any

from prometheus_client import multiprocess


def on_starting(_server: Any) -> None:
    # Counters from a previous container run must not leak into this one.
    path = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if path:
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path, exist_ok=True)


def child_exit(_server: Any, worker: Any) -> None:
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.mark_process_dead(worker.pid)  # type: ignore[no-untyped-call]
