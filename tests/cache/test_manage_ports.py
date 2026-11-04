"""manage.py: a port still held by an old Rulezet is waited for, then reported (not a half-started server)."""
import importlib.util
import os
import socket
import threading
import time

import pytest

_spec = importlib.util.spec_from_file_location('manage', os.path.join(os.getcwd(), 'manage.py'))
manage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage)


def _listen():
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', 0))
    s.listen()
    return s, str(s.getsockname()[1])


def test_free_port_returns_at_once():
    s, port = _listen()
    s.close()
    t = time.time()
    manage._wait_port_free('127.0.0.1', port, timeout=5)
    assert time.time() - t < 2


def test_waits_for_an_old_server_that_stops():
    s, port = _listen()
    threading.Timer(2, s.close).start()           # the old server finishes its requests, then lets go
    manage._wait_port_free('127.0.0.1', port, timeout=10)


def test_still_taken_stops_with_the_holder(capsys):
    s, port = _listen()
    try:
        with pytest.raises(SystemExit):
            manage._wait_port_free('127.0.0.1', port, timeout=2)
        cap = capsys.readouterr()
        out = cap.out + cap.err
        assert f'Port {port} is still used by' in out and 'pid' in out
    finally:
        s.close()
