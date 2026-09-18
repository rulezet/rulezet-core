"""
wsgi.py — gunicorn entrypoint for production (see manage.py's start-prod/deploy).

app.py is the CLI/dev entrypoint (db init/reset/seed, `python3 app.py` for
the dev server) — it parses its own argv with argparse at import time, which
breaks under gunicorn (gunicorn's own CLI flags would get fed to app.py's
parser instead, since `gunicorn wsgi:app -w 4 ...` imports the module with
gunicorn's argv still in sys.argv). This module is a plain, argv-free
import of the same create_app() factory, safe for gunicorn's `wsgi:app`.

start_worker=False — the background job worker, telemetry loop and
update-checker loop run in a separate dedicated process (worker.py) instead,
started alongside this one by `manage.py start-prod`. They used to run as
in-process threads here, but that put them at the mercy of gunicorn's
request-handling watchdogs (--timeout, --max-requests) — a job taking longer
than the timeout, or than it takes traffic to rack up --max-requests
requests, got its whole process (and therefore the job) killed mid-run.
See worker.py's docstring for the full reasoning.
"""
import os

from dotenv import load_dotenv

os.environ.setdefault('FLASKENV', 'production')
load_dotenv()

from app import create_app

app = create_app(start_worker=False)
