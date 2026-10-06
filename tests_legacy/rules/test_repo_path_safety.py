"""Clone paths and branch names come from user input: they must never let a
repository clone — or its deletion — land outside the Rules_Github cache,
nor a branch be read as a git option."""

import os

import pytest

from app.features.rule.rule_format.utils_format import utils_import_update as U


@pytest.mark.parametrize("branch", ["main", "feature/x", "release-1.2", "v2.0+hotfix"])
def test_valid_branches(branch):
    assert U.is_valid_branch_name(branch)


@pytest.mark.parametrize("branch", ["../../etc", "-f", "--upload-pack=touch x", "/abs", "a..b", "x/", "a b", "x.lock", ""])
def test_rejected_branches(branch):
    assert not U.is_valid_branch_name(branch)


def test_dot_dot_url_stays_inside_the_cache(monkeypatch):
    monkeypatch.setattr(U, "is_github_repo_accessible", lambda *_a, **_k: (True, ""))
    seen = []
    monkeypatch.setattr(U.Repo, "clone_from", lambda url, path, **_k: seen.append(path))
    U.clone_or_access_repo("https://github.com/../..")
    assert seen and os.path.realpath(seen[0]).startswith(os.path.realpath(U.RULES_GITHUB_DIR) + os.sep)


@pytest.mark.parametrize("url,branch", [
    ("https://github.com/owner/repo", "../../../../tmp/x"),
    ("https://github.com/owner/repo", "--upload-pack=touch /tmp/pwned"),
])
def test_clone_never_escapes_the_cache(url, branch, monkeypatch):
    monkeypatch.setattr(U, "is_github_repo_accessible", lambda *_a, **_k: (True, ""))
    monkeypatch.setattr(U.Repo, "clone_from", lambda *_a, **_k: pytest.fail("must not clone"))
    with pytest.raises(Exception):
        U.clone_or_access_repo(url, branch=branch)


def test_delete_refuses_anything_outside_the_cache(tmp_path):
    victim = tmp_path / "keep"
    victim.mkdir()
    assert U.delete_existing_repo_folder(str(victim)) is False
    assert victim.exists()
    assert U.delete_existing_repo_folder(os.path.join(U.RULES_GITHUB_DIR, "..", "..", "features")) is False


@pytest.mark.parametrize("url", ["https://github.com/../x", "https://github.com/x/..", "https://github.com/a/b?c"])
def test_branch_lookup_refuses_odd_repository_names(url, monkeypatch):
    """owner/repo is pasted into a GitHub API path sent with our token."""
    monkeypatch.setattr(U.requests, "get", lambda *_a, **_k: pytest.fail("must not call GitHub"))
    branches, error = U.get_github_branches(url)
    assert branches == [] and error
