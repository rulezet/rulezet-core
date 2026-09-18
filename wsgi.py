"""
wsgi.py — gunicorn entrypoint for production (see manage.py's start-prod/deploy).

app.py is the CLI/dev entrypoint (db init/reset/seed, `python3 app.py` for
the dev server) — it parses its own argv with argparse at import time, which
breaks under gunicorn (gunicorn's own CLI flags would get fed to app.py's
parser instead, since `gunicorn wsgi:app -w 4 ...` imports the module with
gunicorn's argv still in sys.argv). This module is a plain, argv-free
import of the same create_app() factory, safe for gunicorn's `wsgi:app`.
"""
import os

from dotenv import load_dotenv

os.environ.setdefault('FLASKENV', 'production')
load_dotenv()

from app import create_app

app = create_app()
