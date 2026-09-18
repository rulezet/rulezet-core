"""
worker.py — dedicated background-worker process for production (see
manage.py's start-prod/deploy).

Runs the BackgroundJob queue (both lanes), the telemetry ping loop, and the
update-checker loop — kept OUT of the gunicorn web workers (wsgi.py, which
now uses start_worker=False) on purpose:

  - gunicorn's --timeout kills a worker that hasn't responded in time. That
    watchdog exists to catch a genuinely hung HTTP request handler — it has
    no business also applying to a long-running background job (a big
    GitHub import, a bulk rule re-validation...) just because that job's
    thread happens to share a process with the web workers.
  - gunicorn's --max-requests periodically recycles a worker process to
    guard against memory leaks. If the job worker lived in that same
    process, any job running longer than it takes traffic to rack up that
    many requests would get killed and requeued before ever finishing.
  - CPU-heavy job work (parsing/validating many rule files) holds the GIL
    and would otherwise directly slow down request handling in the same
    process.

This process does nothing itself beyond create_app(start_worker=True),
which spawns the real work as daemon threads — it just needs to stay alive
and exit cleanly on SIGTERM/SIGINT (systemd/manage.py sends SIGTERM to stop
it; docker/manual Ctrl+C sends SIGINT).
"""
import os
import signal
import time

from dotenv import load_dotenv

os.environ.setdefault('FLASKENV', 'production')
load_dotenv()

from app import create_app

app = create_app(start_worker=True)

_stop = False


def _handle_stop(signum, frame):
    global _stop
    _stop = True


signal.signal(signal.SIGTERM, _handle_stop)
signal.signal(signal.SIGINT, _handle_stop)

print("[worker-process] Background worker running (job queue, telemetry, update-checker).", flush=True)
while not _stop:
    time.sleep(1)
print("[worker-process] Stopped.", flush=True)
