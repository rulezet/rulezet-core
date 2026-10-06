"""Rule-format tests run the formats' own validators. Zeek's calls the
`zeek-script` tool installed in the virtualenv — put that venv's bin first on
PATH, as manage.py does when it starts Rulezet."""
import os
import sys

import pytest


@pytest.fixture(autouse=True)
def _venv_tools_on_path(monkeypatch):
    monkeypatch.setenv("PATH", os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""))
