"""GitHub for rules — a fake GitHub (no network) and the feature's factories.

FakeGitHub serves repositories built locally in `tmp_path` (real git
repositories, real commits) as if they lived on github.com:

    github = FakeGitHub(tmp_path, monkeypatch)       # see the `github` fixture
    url = github.repo("acme/rules", {"rules/a.yar": yara_rule("a")})
    github.commit(url, {"rules/a.yar": yara_rule("a_v2")})

Once installed:
- `git clone https://github.com/acme/rules` clones the local repository
  (GitPython's Repo.clone_from is redirected) — any other URL fails like a
  missing repository;
- every HTTP request goes through a fake GitHub REST API answering
  /repos/<owner>/<name>, /branches, /commits, /contributors and /rate_limit
  for the repositories created here, 404 otherwise; a request to any other
  host raises (no network, ever);
- clones are cached under `tmp_path`, never in the app folder;
- the import / update threads run inline (deterministic, one SQLite writer).
"""
import datetime
import itertools
import json
import os
import subprocess
import uuid
from pathlib import Path
from urllib.parse import urlparse

import git
import requests

from app import db
from app.core.db_class.db import (
    GithubProposal, GithubSyncSchedule, GithubSyncScheduleRepo, ImporterResult, NewRule, RuleStatus,
    RuleUpdateHistory, UpdateResult,
)
from tests_new.helpers.rules import make_rule, yara_rule

GITHUB = "https://github.com"
_counter = itertools.count(1)


# ── The fake GitHub ───────────────────────────────────────────────────────────

class InlineThread:
    """Stands in for threading.Thread: runs the target when started."""

    def __init__(self, target=None, args=(), kwargs=None, daemon=None, **_):
        self._target, self._args, self._kwargs = target, args, kwargs or {}
        self.daemon = daemon

    def start(self):
        self._target(*self._args, **self._kwargs)

    def join(self, timeout=None):
        return None

    def is_alive(self):
        return False


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.name=Upstream", "-c", "user.email=upstream@tests.rulezet",
         "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", *args],
        cwd=cwd, check=True, capture_output=True,
    )


def _response(status, payload, url):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(payload).encode()
    response.headers["Content-Type"] = "application/json"
    response.url = url
    return response


class FakeGitHub:
    def __init__(self, root, monkeypatch):
        self.root = Path(root)
        self.upstream = self.root / "upstream"
        self.cache = self.root / "clones"
        self.repos = {}            # "owner/name" -> {"path", "license", "branches"}
        self.requests = []         # every URL the code tried to reach
        self._install(monkeypatch)

    # Building upstream repositories

    def repo(self, full_name="acme/rules", files=None, *, license="MIT", host=GITHUB):
        """A repository with `files` ({path: content}) in one commit on
        `main`. Returns its URL."""
        path = self.upstream / full_name
        path.mkdir(parents=True)
        _git(path, "init", "-q")
        self.repos[full_name] = {"path": path, "license": license, "branches": ["main"], "host": host}
        self.commit(f"{host}/{full_name}", files or {"README.md": "rules\n"}, message="initial")
        return f"{host}/{full_name}"

    def path(self, url):
        return self.repos[self._full_name(url)]["path"]

    def commit(self, url, files=None, *, delete=(), message="update"):
        path = self.path(url)
        for name, content in (files or {}).items():
            target = path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content) if isinstance(content, str) else target.write_bytes(content)
        for name in delete:
            (path / name).unlink()
        _git(path, "add", "-A")
        _git(path, "commit", "-q", "--allow-empty", "-m", message)

    def branch(self, url, name, files):
        """A second branch holding `files` on top of main."""
        path = self.path(url)
        _git(path, "checkout", "-q", "-b", name)
        self.commit(url, files, message=f"on {name}")
        _git(path, "checkout", "-q", "main")
        self.repos[self._full_name(url)]["branches"].append(name)

    def symlink(self, url, name, target):
        """Commit a symlink `name` -> `target` (an absolute path outside the repo)."""
        path = self.path(url)
        link = path / name
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, link)
        _git(path, "add", "-A")
        _git(path, "commit", "-q", "-m", "symlink")

    # Plumbing

    @staticmethod
    def _full_name(url):
        parts = [p for p in urlparse(url).path.split("/") if p]
        if len(parts) < 2:
            return None
        name = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
        return f"{parts[0]}/{name}"

    def _local_repo(self, url):
        full_name = self._full_name(url)
        repo = self.repos.get(full_name)
        if not repo or not url.startswith(repo["host"] + "/"):
            return None
        return repo["path"]

    def _install(self, monkeypatch):
        from app.features.rule import rule as rule_routes
        from app.features.rule.rule_format.utils_format import utils_import_update
        from app.features.rule.rule_from_github.import_rule import session_class
        from app.features.rule.rule_from_github.update_rule import update_class

        monkeypatch.setattr(utils_import_update, "RULES_GITHUB_DIR", str(self.cache))

        real_clone = git.Repo.clone_from

        def clone_from(url, to_path, **kwargs):
            self.requests.append(("clone", url))
            local = self._local_repo(url)
            if local is None:
                raise git.GitCommandError(["git", "clone", url], 128, stderr="fatal: repository not found")
            kwargs.pop("depth", None)
            return real_clone(str(local), to_path, **kwargs)

        monkeypatch.setattr(git.Repo, "clone_from", clone_from)
        monkeypatch.setattr(requests.Session, "request", lambda _session, method, url, **kw: self._fake_request(method, url))

        monkeypatch.setattr(rule_routes, "Thread", InlineThread)
        monkeypatch.setattr(update_class, "Thread", InlineThread)

        def start_inline(session, app_obj=None, user_obj=None):
            from flask import current_app
            from flask_login import current_user
            session.run_sync(app_obj or current_app._get_current_object(),
                             user_obj or current_user._get_current_object())

        monkeypatch.setattr(session_class.Session_class, "start", start_inline)
        monkeypatch.setattr(session_class, "sessions", [])
        monkeypatch.setattr(update_class, "sessions", [])

    def _fake_request(self, method, url):
        self.requests.append((method, url))
        parsed = urlparse(url)
        if parsed.netloc != "api.github.com":
            raise requests.ConnectionError(f"network disabled in tests: {url}")
        parts = [p for p in parsed.path.split("/") if p]
        if parts == ["rate_limit"]:
            return _response(200, {"resources": {"core": {"limit": 5000, "remaining": 4999, "reset": 4102444800}}}, url)
        if len(parts) < 3 or parts[0] != "repos":
            return _response(404, {"message": "Not Found"}, url)
        full_name = f"{parts[1]}/{parts[2]}"
        repo = self.repos.get(full_name)
        if repo is None or repo["host"] != GITHUB:
            return _response(404, {"message": "Not Found"}, url)
        rest = parts[3:]
        if not rest:
            owner = parts[1]
            return _response(200, {
                "id": 1, "name": parts[2], "full_name": full_name, "private": False,
                "owner": {"login": owner, "html_url": f"{GITHUB}/{owner}", "avatar_url": None},
                "html_url": f"{GITHUB}/{full_name}", "url": url, "description": "Sample rules",
                "license": {"spdx_id": repo["license"], "name": repo["license"]} if repo["license"] else None,
                "default_branch": "main", "stargazers_count": 0, "forks_count": 0,
            }, url)
        if rest == ["branches"]:
            return _response(200, [{"name": b} for b in repo["branches"]], url)
        if rest in (["commits"], ["contributors"]):
            return _response(200, [], url)
        return _response(404, {"message": "Not Found"}, url)


def saved(obj):
    """`obj` as committed in the database. Tests share one session with the
    requests they make, so a change a route made but never committed would
    still be visible through reload(): roll it back first, as the end of a
    real request does."""
    from tests_new.helpers.db import reload
    db.session.rollback()
    return reload(obj)


# ── Factories ─────────────────────────────────────────────────────────────────

def _now():
    return datetime.datetime.now(tz=datetime.timezone.utc)


def make_github_rule(owner, repo_url, *, path=None, content=None, title=None, branch=None, **overrides):
    """A YARA rule imported from `repo_url` (its source), stored at `path` in
    the repository."""
    n = next(_counter)
    name = title or f"github_rule_{n}"
    return make_rule(
        owner,
        title=name,
        source=repo_url,
        github_path=path or f"rules/{name}.yar",
        branch=branch,
        to_string=content or yara_rule(name),
        **overrides,
    )


def make_import_result(user, *, repo_url=f"{GITHUB}/acme/rules"):
    """A finished import, as the history of imports lists it."""
    result = ImporterResult(
        uuid=str(uuid.uuid4()), info=json.dumps({"repo_url": repo_url, "url": repo_url}),
        bad_rules=0, imported=1, skipped=0, total=1, query_date=_now(), user_id=user.id,
        count_per_format=json.dumps({}),
    )
    db.session.add(result)
    db.session.commit()
    return result


def make_update_result(user, *, mode="by_url", repo_url=f"{GITHUB}/acme/rules"):
    """A finished update check (no rules yet)."""
    result = UpdateResult(
        uuid=str(uuid.uuid4()), user_id=str(user.id), mode=mode,
        info=json.dumps({"mode": mode, "repo_url": repo_url}),
        repo_sources=json.dumps(repo_url if mode == "by_url" else []),
        found=0, updated=0, not_found=0, skipped=0, total=0, query_date=_now(),
    )
    db.session.add(result)
    db.session.commit()
    return result


def make_pending_update(rule, new_content, *, checked_by, result=None, syntax_valid=True):
    """What an update check leaves for a rule whose upstream content changed:
    a pending history entry (the proposal) and its status row in the check's
    result. The rule itself is left untouched."""
    result = result or make_update_result(checked_by)
    history = RuleUpdateHistory(
        rule_id=rule.id, rule_title=rule.title, success=True,
        message="Update found for this rule.", new_content=new_content, old_content=rule.to_string,
        analyzed_by_user_id=checked_by.id, analyzed_at=_now(),
    )
    db.session.add(history)
    db.session.flush()
    status = RuleStatus(
        uuid=str(uuid.uuid4()), update_result_id=result.id, date=_now(), name_rule=rule.title,
        rule_id=str(rule.id), message="Update found for this rule.", found=True, update_available=True,
        rule_syntax_valid=syntax_valid, error=not syntax_valid, history_id=str(history.id),
    )
    db.session.add(status)
    result.found += 1
    result.updated += 1
    result.total += 1
    db.session.commit()
    return result, status, history


def make_new_rule(result, content, *, name="new_rule", valid=True, fmt="yara", path=None):
    """A rule found upstream that isn't in Rulezet yet, waiting for a decision."""
    new_rule = NewRule(
        uuid=str(uuid.uuid4()), update_result_id=result.id, date=_now(), name_rule=name,
        rule_content=content, message="" if valid else "Validation Failed.", rule_syntax_valid=valid,
        error=not valid, accept=False, format=fmt, github_path=path or f"rules/{name}.yar",
    )
    db.session.add(new_rule)
    db.session.commit()
    return new_rule


def make_proposal(requester, repo_url=None, *, status="pending", **fields):
    proposal = GithubProposal(
        user_id=requester.id, repo_url=repo_url or f"{GITHUB}/acme/proposed-{next(_counter)}",
        status=status, **fields,
    )
    db.session.add(proposal)
    db.session.commit()
    return proposal


def make_schedule(editor, repo_urls=(f"{GITHUB}/acme/rules",), *, auto_accept=False, auto_add=False, **fields):
    values = dict(uuid=str(uuid.uuid4()), title=f"Schedule {next(_counter)}", editor_id=editor.id,
                  frequency="daily", hour=3, minute=0, timezone="UTC", is_active=True)
    values.update(fields)
    schedule = GithubSyncSchedule(**values)
    db.session.add(schedule)
    db.session.flush()
    for url in repo_urls:
        db.session.add(GithubSyncScheduleRepo(schedule_id=schedule.id, repo_url=url,
                                              auto_accept_update=auto_accept, auto_add_new_rule=auto_add))
    db.session.commit()
    return schedule


def schedule_payload(repo_urls=(f"{GITHUB}/acme/rules",), **overrides):
    """What the Sync Schedule form posts."""
    payload = dict(title="Nightly sync", frequency="daily", hour=4, minute=30, timezone="UTC",
                   repo_mode="partial", selected_repo_urls=list(repo_urls))
    payload.update(overrides)
    return payload
