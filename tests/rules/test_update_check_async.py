"""Git update check: start() returns at once, the repository is prepared in the background."""
import threading
import time

from app.core.db_class.user import User
from app.features.rule.rule_from_github.update_rule import update_class as UM


def _session(app):
    user = User.query.filter_by(email='admin@admin.admin').first()
    return UM.Update_class(['https://github.com/example/repo'], user, {'mode': 'by_url'}, mode='by_url')


def test_start_returns_at_once_and_reports_preparing(app, monkeypatch):
    gate = threading.Event()

    def slow_prepare(self):
        gate.wait(10)                      # cloning + reading a big repository
        self.total = 0
        return True
    monkeypatch.setattr(UM.Update_class, '_prepare', slow_prepare)
    monkeypatch.setattr(UM.Update_class, 'save_info', lambda self: None)
    with app.app_context():
        s = _session(app)
        t = time.time()
        s.start()
        assert time.time() - t < 1
        st = s.status()
        assert st['preparing'] is True and st['remaining'] == 1      # the page keeps polling
        gate.set()
        assert s._save_done.wait(10)                                 # workers ran, the check finished
        assert s.status()['remaining'] == 0


def test_error_while_preparing_is_reported_not_stuck(app, monkeypatch):
    def broken(self):
        raise RuntimeError('disk full')
    saved = []
    monkeypatch.setattr(UM.Update_class, '_prepare', broken)
    monkeypatch.setattr(UM.Update_class, 'save_info', lambda self: saved.append(self.rule_status_list[-1]['message']))
    with app.app_context():
        s = _session(app)
        s.start()
        assert s._save_done.wait(10)
        assert s.preparing is False
        assert 'disk full' in saved[0]
