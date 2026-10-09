#!/usr/bin/env python3
"""
manage.py — Rulezet management script

Usage:
    python3 manage.py <command>

Commands:
    init        First-time setup: install deps + init DB
    start       Start the dev server
    start-prod  Start with Gunicorn (production)
    test        Run the test suite
    update      sync with origin + install deps + ensure ollama + DB migrations
    backup      Backup the PostgreSQL database
    restore     Restore a PostgreSQL backup (interactive)
    deploy      Full deployment: backup + update + start-prod
    db          Run Flask-Migrate commands (upgrade by default)
    db-init     Create tables + admin user (python3 app.py -i)
    db-reload   Drop + recreate DB (python3 app.py -r)
    help        Show this help message
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / "env"
VENV_BIN = VENV / "bin"

PYTHON   = str(VENV_BIN / "python3")
FLASK    = str(VENV_BIN / "flask")
GUNICORN = str(VENV_BIN / "gunicorn")
PYTEST   = str(VENV_BIN / "pytest")
PIP      = str(VENV_BIN / "pip")


# ── Helpers ───────────────────────────────────────────────────────────────────

def header(text: str) -> None:
    print(f"\n\033[1;34m{'─' * 52}\033[0m")
    print(f"\033[1;34m  {text}\033[0m")
    print(f"\033[1;34m{'─' * 52}\033[0m")


def ok(text: str) -> None:
    print(f"\033[1;32m  ✓ {text}\033[0m")


def info(text: str) -> None:
    print(f"\033[0;37m  · {text}\033[0m")


def error(text: str) -> None:
    print(f"\033[1;31m  ✗ {text}\033[0m", file=sys.stderr)


def app_version() -> str:
    try:
        return (ROOT / "version").read_text().strip() or "unknown"
    except OSError:
        return "unknown"


def _venv_env() -> dict:
    """Build an environment dict that activates the virtualenv."""
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(VENV)
    env["PATH"] = str(VENV_BIN) + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONHOME", None)
    return env


def run(cmd: list[str], cwd: Path = ROOT, check: bool = True, extra_env: dict | None = None) -> subprocess.CompletedProcess:
    env = _venv_env()
    if extra_env:
        env.update(extra_env)
    info(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, env=env)
    # returncode 130 = Ctrl+C sent to child process
    if result.returncode in (130, -2):
        raise KeyboardInterrupt
    if check and result.returncode != 0:
        error(f"Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result


def _current_branch() -> str:
    result = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() or "main"


def _sync_with_origin() -> None:
    """Make the working tree exactly match origin's current branch.

    Production is a deploy target, not a place for its own commits — any
    local commit or edit there (accidental, or made directly on the server)
    would otherwise turn every future `git pull` into a "divergent branches"
    prompt that blocks an unattended deploy. Fetch + hard-reset instead of
    `git pull` sidesteps that entirely, at the cost of discarding anything
    local: never run this against a checkout with work you want to keep.
    """
    run(["git", "fetch", "origin"])
    branch = _current_branch()
    run(["git", "reset", "--hard", f"origin/{branch}"])


def _sync_submodules() -> None:
    """Bring tracked-branch submodules up to their remote tip.

    Mirrors update.sh's submodule step: rulezet-cast, misp-taxonomies,
    misp-galaxy and rulezet-validation float to their remote branch on every
    update (--remote) since we want their latest content automatically —
    rulezet-validation in particular used to require a separate manual pull
    on prod; pivotick stays pinned to the committed submodule ref (its dist
    build is hand-copied into static/ on version bumps, see
    app/static/js/pivotick.iife.js) and cti is skipped here (too large for
    --remote; refreshed via the admin UI instead).
    """
    run(["git", "submodule", "update", "--init", "--recursive",
         "app/modules/rulezet-validation"])
    result = subprocess.run(
        ["git", "submodule", "update", "--remote", "app/modules/rulezet-cast",
         "app/modules/misp-taxonomies", "app/modules/misp-galaxy",
         "app/modules/rulezet-validation"],
        cwd=ROOT,
    )
    if result.returncode != 0:
        run(["git", "submodule", "update", "--remote"])
    run(["git", "submodule", "update", "--init", "app/modules/pivotick",
         "app/modules/pivotick-converters", "app/modules/pivograph"])


# ── Pivotick graph assets (no npm, no Node) ──────────────────────────────────
# The graphs use two pinned submodules:
#   app/modules/pivotick             — the Pivotick library (pinned to a release tag)
#   app/modules/pivotick-converters  — MISP event → Pivotick graph (TypeScript)
# Neither commits a browser build, and the server must not need npm/Node, so
# `manage.py pivotick` produces the browser files and they are committed:
#   - Pivotick: the official pivotick-dist.zip attached to the GitHub release
#     of the pinned tag (built by Pivotick's own CI) → pivotick.iife.js + css
#   - converters: compiled once with the standalone esbuild binary (a single
#     executable, checksum-verified against the npm registry metadata — the
#     registry is only used as a file host, npm itself is never run)
# BUILD_STAMP records which submodule versions the committed files come from;
# update/start-prod rebuild only when the pinned submodules moved.

PIVOTICK_DIR      = ROOT / "app" / "modules" / "pivotick"
CONVERTERS_DIR    = ROOT / "app" / "modules" / "pivotick-converters"
PIVOTICK_JS       = ROOT / "app" / "static" / "js" / "pivotick.iife.js"
PIVOTICK_CSS      = ROOT / "app" / "static" / "css" / "components" / "pivotick.css"
CONVERTERS_JS     = ROOT / "app" / "static" / "js" / "pivotick" / "pivotick-converters.js"
BUILD_STAMP       = ROOT / "app" / "static" / "js" / "pivotick" / "build.json"
ESBUILD_VERSION   = "0.25.10"
ESBUILD_CACHE     = Path.home() / ".cache" / "rulezet" / f"esbuild-{ESBUILD_VERSION}"


def _git_out(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ""


def _pivotick_refs() -> dict:
    """Pinned commits of both submodules — what the committed assets must match.
    Commits, not tags: a shallow submodule clone (install.sh uses --depth 1)
    often has no tags at all."""
    return {
        "pivotick": _git_out(["rev-parse", "HEAD"], PIVOTICK_DIR),
        "converters": _git_out(["rev-parse", "HEAD"], CONVERTERS_DIR),
    }


def _pivotick_tag() -> str:
    """Release tag of the pinned Pivotick commit (needed to download its
    official build) — fetched from origin if the clone has no tags."""
    tag = _git_out(["describe", "--tags", "--exact-match"], PIVOTICK_DIR)
    if not tag:
        subprocess.run(["git", "fetch", "--quiet", "--tags", "origin"], cwd=PIVOTICK_DIR)
        tag = _git_out(["describe", "--tags", "--exact-match"], PIVOTICK_DIR)
    return tag


def _download(url: str) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "rulezet-manage"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _esbuild_binary() -> Path:
    """Standalone esbuild executable for this OS/arch, cached in ~/.cache."""
    import base64
    import hashlib
    import io
    import platform
    import tarfile

    binary = ESBUILD_CACHE / "esbuild"
    if binary.exists():
        return binary
    system = {"Linux": "linux", "Darwin": "darwin"}.get(platform.system())
    arch = {"x86_64": "x64", "amd64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    if not system or not arch:
        raise RuntimeError(f"no esbuild binary for {platform.system()}/{platform.machine()}")
    pkg = f"@esbuild/{system}-{arch}"
    meta = json.loads(_download(f"https://registry.npmjs.org/{pkg}/{ESBUILD_VERSION}"))
    tarball = _download(meta["dist"]["tarball"])
    algo, _, expected = meta["dist"]["integrity"].partition("-")
    if base64.b64encode(hashlib.new(algo, tarball).digest()).decode() != expected:
        raise RuntimeError("esbuild download failed its integrity check")
    with tarfile.open(fileobj=io.BytesIO(tarball)) as tar:
        member = tar.getmember("package/bin/esbuild")
        data = tar.extractfile(member).read()
    ESBUILD_CACHE.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(data)
    binary.chmod(0o755)
    return binary


def _build_pivotick_assets(refs: dict) -> None:
    import io
    import tempfile
    import zipfile

    tag = _pivotick_tag()
    if not tag:
        raise RuntimeError("app/modules/pivotick is not on a release tag — check out one (e.g. v2.0.1)")
    info(f"Pivotick {tag}: downloading the official release build…")
    archive = zipfile.ZipFile(io.BytesIO(_download(
        f"https://github.com/Pivotick/Pivotick/releases/download/{tag}/pivotick-dist.zip")))
    names = {Path(n).name: n for n in archive.namelist()}
    for wanted, target in (("pivotick.iife.js", PIVOTICK_JS), ("pivotick.css", PIVOTICK_CSS)):
        if wanted not in names:
            raise RuntimeError(f"{wanted} missing from the {tag} release archive")
        target.write_bytes(archive.read(names[wanted]))
    ok(f"Pivotick {tag} → {PIVOTICK_JS.relative_to(ROOT)}, {PIVOTICK_CSS.relative_to(ROOT)}")

    commit = refs["converters"]
    info(f"pivotick-converters {commit[:8]}: compiling with esbuild {ESBUILD_VERSION}…")
    esbuild = _esbuild_binary()
    core = CONVERTERS_DIR / "packages" / "core" / "src" / "index.ts"
    misp = CONVERTERS_DIR / "packages" / "misp" / "src" / "index.ts"
    with tempfile.TemporaryDirectory() as tmp:
        entry = Path(tmp) / "entry.ts"
        # Importing the misp package also registers MispEventImporter in
        # GraphRegistry (side effect of its index).
        entry.write_text(
            f"export {{ GraphRegistry, PIVOTICK_STYLE_OVERRIDES, RECOMMENDED_PIVOTICK_SIMULATION_OPTIONS }} from {json.dumps(str(core))}\n"
            f"export {{ MispEventImporter, NODE_DEFAULTS }} from {json.dumps(str(misp))}\n"
        )
        CONVERTERS_JS.parent.mkdir(parents=True, exist_ok=True)
        run([str(esbuild), str(entry), "--bundle", "--format=esm", "--target=es2020", "--minify",
             "--legal-comments=inline", f"--outfile={CONVERTERS_JS}",
             f"--banner:js=/* pivotick-converters {commit} (MIT) — built by `python3 manage.py pivotick`, do not edit */"])
    ok(f"pivotick-converters → {CONVERTERS_JS.relative_to(ROOT)}")

    BUILD_STAMP.write_text(json.dumps({**refs, "pivotick_tag": tag}, indent=2) + "\n")


def _ensure_pivotick_assets(force: bool = False) -> None:
    """Rebuild the committed graph assets only if the pinned submodules moved
    (or on demand). Never fatal on update: the committed files keep working."""
    refs = _pivotick_refs()
    try:
        stamp = json.loads(BUILD_STAMP.read_text())
    except (OSError, ValueError):
        stamp = {}
    if (not force and stamp.get("pivotick") == refs["pivotick"] and stamp.get("converters") == refs["converters"]
            and PIVOTICK_JS.exists() and CONVERTERS_JS.exists()):
        ok(f"Pivotick graph assets up to date (Pivotick {stamp.get('pivotick_tag') or refs['pivotick'][:8]}, "
           f"converters {refs['converters'][:8]})")
        return
    try:
        _build_pivotick_assets(refs)
    except Exception as exc:
        if force:
            error(f"Pivotick assets build failed: {exc}")
            sys.exit(1)
        error(f"Could not rebuild the Pivotick graph assets ({exc}) — keeping the committed ones. "
              "Run `python3 manage.py pivotick` on a machine with internet access.")


# ── Pivograph (graph view of the Rule formats page) ──────────────────────────
# app/modules/pivograph is the Pivograph app (github.com/ecrou-exact/project-graph),
# pinned. /rule/formats embeds it in an <iframe> and hands it the graph with
# postMessage. Like Pivotick, its browser build is committed so the server
# never needs Node: `manage.py pivograph` (on a dev machine with npm) builds
# the pinned commit and copies the app — not its docs or Hugo example — to
# app/static/pivograph/, stamped with the commit in build.json.

PIVOGRAPH_DIR    = ROOT / "app" / "modules" / "pivograph"
PIVOGRAPH_STATIC = ROOT / "app" / "static" / "pivograph"
PIVOGRAPH_KEEP   = ("index.html", "favicon.svg", "assets", "icons", "fonts", "logos")


def _build_pivograph_assets() -> None:
    import shutil
    commit = _git_out(["rev-parse", "HEAD"], PIVOGRAPH_DIR)
    if not commit:
        raise RuntimeError("app/modules/pivograph is missing — run `git submodule update --init app/modules/pivograph`")
    if not shutil.which("npm"):
        raise RuntimeError("npm is required to build Pivograph (only on the machine that builds it, not on the server)")
    info(f"Pivograph {commit[:8]}: npm ci + npm run build…")
    run(["npm", "ci", "--no-audit", "--no-fund"], cwd=PIVOGRAPH_DIR)
    run(["npm", "run", "build"], cwd=PIVOGRAPH_DIR)
    dist = PIVOGRAPH_DIR / "dist"
    if PIVOGRAPH_STATIC.exists():
        shutil.rmtree(PIVOGRAPH_STATIC)
    PIVOGRAPH_STATIC.mkdir(parents=True)
    for name in PIVOGRAPH_KEEP:
        src = dist / name
        if src.is_dir():
            shutil.copytree(src, PIVOGRAPH_STATIC / name)
        elif src.exists():
            shutil.copy2(src, PIVOGRAPH_STATIC / name)
    (PIVOGRAPH_STATIC / "build.json").write_text(json.dumps({"pivograph": commit}, indent=2) + "\n")
    ok(f"Pivograph → {PIVOGRAPH_STATIC.relative_to(ROOT)}")


def _check_pivograph_assets() -> None:
    """Warn (never fail) when the committed Pivograph build doesn't match the pinned submodule."""
    commit = _git_out(["rev-parse", "HEAD"], PIVOGRAPH_DIR)
    try:
        built = json.loads((PIVOGRAPH_STATIC / "build.json").read_text()).get("pivograph")
    except (OSError, ValueError):
        built = None
    if commit and built and commit != built:
        error(f"app/static/pivograph was built from {built[:8]} but the submodule is at {commit[:8]} — "
              "run `python3 manage.py pivograph` on a machine with npm and commit the result.")


def _confirm(prompt: str) -> bool:
    """Ask for confirmation. Returns True if confirmed, False if cancelled (or Ctrl+C)."""
    try:
        answer = input(f"\033[1;33m  {prompt} [yes/N]: \033[0m").strip().lower()
        return answer == "yes"
    except KeyboardInterrupt:
        return False


def _check_venv() -> None:
    if not VENV_BIN.exists():
        error(f"Virtualenv not found at {VENV}")
        print(f"\n  Create it first:\n    python3 -m venv {VENV}\n    python3 manage.py init\n")
        sys.exit(1)


OLLAMA_MODEL = "qwen2.5:1.5b"

# Set as the rule_fixer agent's default_model (AIAgentConfig, set directly
# in the DB, not here) once pulled. Kept separate from OLLAMA_MODEL since
# that one is the chatbot's default and the two agents don't have to share
# a model.
#
# Was hf.co/vtriple/threatflux-0.6B-gguf (a 0.6B YARA-specific fine-tune) —
# swapped out after it missed an actual production bug (a string identifier
# missing its leading '$') that qwen2.5-coder:7b caught correctly once the
# prompt was also fixed to highlight the exact flagged line (see
# rule_fixer_agent.py's _line_context — a small YARA-specific model is not
# a substitute for solid general instruction-following on precise, localized
# text edits). Larger (~4.7GB vs ~1.2GB) and slower, but confirmed to
# actually work on real broken rules where the smaller one didn't.
OLLAMA_RULE_FIXER_MODEL = "qwen2.5-coder:7b"

# Pinned, not "latest": 0.32.1+ segfaults on every model on Intel Sapphire
# Rapids Xeons (e.g. Xeon Silver 4410Y — production's CPU) — its AMX-aware
# CPU inference path crashes on this CPU generation even with
# OLLAMA_LLM_LIBRARY=cpu forced and a from-scratch reinstall/re-pulled
# model. 0.5.7 predates that code path (falls back to a plain avx2 runner)
# and was confirmed working. Bump this only after confirming a newer
# release fixes the Sapphire Rapids crash — briefly bumped to 0.33.0 for
# Qwen3 support (a since-abandoned rule_fixer model needed it), reverted
# once rule_fixer moved to qwen2.5-coder:7b, which needs nothing newer than
# this — same architecture family as qwen2.5:1.5b/3b, already confirmed
# working here.
OLLAMA_VERSION = "0.5.7"


def _install_ollama() -> bool:
    info(f"Installing Ollama {OLLAMA_VERSION} (this may prompt for your sudo password)…")
    result = subprocess.run(
        f"curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION={OLLAMA_VERSION} sh",
        shell=True,
    )
    if result.returncode != 0:
        error("Ollama installation failed or was skipped — the chat assistant will "
              "report a connection error until it's installed manually "
              f"(curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION={OLLAMA_VERSION} sh).")
        return False
    return True


def _ensure_ollama() -> None:
    """Best-effort: install Ollama (used by the in-app chat assistant), pinned
    to OLLAMA_VERSION (see comment above — NOT "latest", a known segfault on
    Sapphire Rapids CPUs), and pull the default model if missing. Mirrors
    install.sh/update.sh's step — manage.py's start-prod/update never call
    those scripts, so without this an instance driven only through manage.py
    never gets Ollama set up."""
    import shutil as _shutil

    info("Checking for Ollama (used by the chat assistant)…")
    ollama_bin = _shutil.which("ollama")

    if not ollama_bin:
        if not _install_ollama():
            return
        ollama_bin = _shutil.which("ollama")
        if not ollama_bin:
            return
        ok(f"Ollama {OLLAMA_VERSION} installed")
    else:
        version = subprocess.run([ollama_bin, "--version"], capture_output=True, text=True, check=False)
        if OLLAMA_VERSION not in (version.stdout or ""):
            info(f"Ollama is installed but not pinned version {OLLAMA_VERSION} "
                 f"({(version.stdout or '').strip() or 'unknown version'}) — reinstalling the pinned version…")
            if not _install_ollama():
                return
            ok(f"Ollama downgraded/reinstalled to {OLLAMA_VERSION}")
        else:
            ok(f"Ollama {OLLAMA_VERSION} is already installed")

    try:
        listed = subprocess.run([ollama_bin, "list"], capture_output=True, text=True, check=False)
        already_listed = listed.stdout or ""
        for model_name, used_by in (
            (OLLAMA_MODEL, "the chat assistant"),
            (OLLAMA_RULE_FIXER_MODEL, "the Rule Fixer agent"),
        ):
            if model_name not in already_listed:
                info(f"Pulling the {model_name} model (used by {used_by})…")
                pulled = subprocess.run([ollama_bin, "pull", model_name])
                if pulled.returncode == 0:
                    ok(f"{model_name} pulled")
                else:
                    error(f"Could not pull {model_name} — run 'ollama pull {model_name}' manually.")
            else:
                ok(f"{model_name} already pulled")
    except OSError as e:
        error(f"Could not check/pull Ollama models: {e}")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_help() -> None:
    W = "\033[1;37m"
    B = "\033[1;34m"
    G = "\033[1;32m"
    Y = "\033[1;33m"
    D = "\033[0;37m"
    R = "\033[0m"

    print(f"""
{B}╔════════════════════════════════════════════════════╗
║              Rulezet — manage.py                   ║
╚════════════════════════════════════════════════════╝{R}

{W}Usage:{R}
    {G}python3 manage.py{R} {Y}<command>{R}

{W}Commands:{R}

  {G}init{R}          {D}First-time setup:{R}
                  {D}  install deps from requirements.txt → init DB{R}
                  {D}→ Run once after cloning the repo{R}

  {G}start-dev{R}     {D}Start locally (FLASKENV=development): worker.py + gunicorn wsgi:app{R}
                  {D}  same launch as start-prod, just dev env/port — see start-prod{R}
                  {D}  debug mode, reloads on code changes (Python and templates){R}
                  {D}→ Use this for local development{R}

  {G}start-prod{R}    {D}Full production launch:{R}
                  {D}  backup → sync with origin → pip install → ensure ollama → db upgrade{R}
                  {D}  → worker.py (background jobs, its own process) + gunicorn wsgi:app --bind 0.0.0.0:80{R}
                  {D}→ Use this on the production server (needs root for port 80){R}
                  {D}→ "Sync with origin" hard-resets to origin/<branch> — any local{R}
                  {D}  commit or edit on the server is discarded, never blocks on conflicts{R}

  {G}restart-prod{R}  {D}Just start-prod's launch step — worker.py + gunicorn, no backup/{R}
                  {D}  sync/deps/migrations first{R}
                  {D}→ Use this on prod when the code's already up to date and you just{R}
                  {D}  need the app process back up (e.g. after killing a stuck worker.py){R}

  {G}test{R}          {D}Run the full test suite (FLASKENV=testing){R}

  {G}update{R}        {D}sync with origin + pip install + ensure ollama + flask db upgrade{R}
                  {D}→ Use this after pulling new code — see start-prod's note on sync{R}

  {G}pivotick{R}      {D}Rebuild the graph assets from app/modules/pivotick (release build){R}
                  {D}  + app/modules/pivotick-converters (compiled with esbuild) — no npm{R}
                  {D}→ Run after bumping either submodule, then commit the result{R}
                  {D}  (update/start-prod rebuild automatically if they moved){R}

  {G}pivograph{R}     {D}Rebuild the Pivograph app (graph view of /rule/formats) from{R}
                  {D}  app/modules/pivograph into app/static/pivograph — needs npm{R}
                  {D}→ Run after bumping the submodule, then commit the result{R}

  {G}backup{R}        {D}Backup PostgreSQL database to backup/dumps/{R}

  {G}restore{R}       {D}Restore a backup interactively{R}

  {G}deploy{R}        {D}Full deployment: backup → update → start-prod{R}

  {G}db{R}            {D}Run Flask-Migrate commands (defaults to upgrade){R}
                  {D}→ python3 manage.py db            # flask db upgrade{R}
                  {D}→ python3 manage.py db migrate -m "msg"{R}
                  {D}→ python3 manage.py db downgrade{R}

  {G}db-init{R}       {D}Create tables + admin user (app.py -i){R}
                  {D}→ Use after a fresh DB creation{R}

  {G}db-reload{R}     {D}DROP + recreate the entire database (app.py -r){R}
                  {D}→ Destructive — wipes all data{R}

  {G}help{R}          {D}Show this message{R}

{W}Examples:{R}

  {D}# Fresh install{R}
  {G}python3 -m venv env{R}
  {G}python3 manage.py init{R}
  {G}python3 manage.py start-dev{R}

  {D}# Daily development{R}
  {G}python3 manage.py start-dev{R}

  {D}# After pulling new code{R}
  {G}python3 manage.py update{R}

  {D}# Generate + apply a migration{R}
  {G}python3 manage.py db migrate -m "add column X"{R}
  {G}python3 manage.py db upgrade{R}

  {D}# Production deployment{R}
  {G}python3 manage.py deploy{R}

{W}Project root:{R} {D}{ROOT}{R}
""")


def cmd_init() -> None:
    _check_venv()
    header("Initialising Rulezet (first-time setup)")

    info("Initialising Git submodules…")
    run(["git", "submodule", "update", "--init", "--recursive", "--depth", "1",
         "app/modules/rulezet-validation"])
    ok("Submodules initialised")

    info("Installing Python dependencies…")
    run([PIP, "install", "-r", "requirements.txt"])
    ok("Dependencies installed")

    info("Initialising database (tables + admin user)…")
    run([PYTHON, "app.py", "-i"], extra_env={"FLASKENV": "development"})
    ok("Database initialised")

    header("Init complete")
    ok("Ready. Run:  python3 manage.py start-dev")


# Launch settings manage.py itself reads — taken from .env too (the shell
# environment still wins), so the deploy scripts can just edit .env. Only
# these keys: everything else in .env is loaded by the app, as before.
_LAUNCH_ENV_KEYS = ("PORT", "GUNICORN_BIND_HOST", "GUNICORN_THREADS",
                    "API_PORT", "API_GUNICORN_THREADS", "LOG_DIR")


def _load_launch_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key in _LAUNCH_ENV_KEYS:
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def _gunicorn_cmd(bind: str, threads: str, log_name: str, reload: bool = False) -> list:
    """One gunicorn serving wsgi:app. Logs go to stdout (the screen) unless
    LOG_DIR is set, then to LOG_DIR/<log_name>-access.log / -error.log.
    `reload` (dev only): restart the workers when a Python file changes."""
    log_dir = os.environ.get("LOG_DIR", "").strip()
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        access_log = os.path.join(log_dir, f"{log_name}-access.log")
        error_log = os.path.join(log_dir, f"{log_name}-error.log")
    else:
        access_log = error_log = "-"
    return [
        GUNICORN,
        "wsgi:app",
        "--bind", bind,
        "--worker-class", "gthread",
        "--workers", "1",
        "--threads", threads,
        "--timeout", "120",
        "--max-requests", "1000",
        "--max-requests-jitter", "100",
        "--access-logfile", access_log,
        "--error-logfile", error_log,
        # [site] / [api] prefix so both streams stay readable when they share stdout
        "--access-logformat", f'[{log_name}] %(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(L)ss "%(f)s" "%(a)s"',
    ] + (["--reload"] if reload else [])


def _run_gunicorn_with_worker(flaskenv: str, port: str, reload: bool = False) -> None:
    """Starts worker.py (background job worker, telemetry loop, update-
    checker, both schedulers — its own process, never inside a gunicorn
    web worker, see start-prod's note below) plus gunicorn serving
    wsgi:app. Shared by `start-dev` and `start-prod` so dev runs on the exact
    same process shape as prod (same gunicorn flags, same worker split) —
    only FLASKENV/port differ — instead of dev using app.py's bundled
    Werkzeug dev server, so gunicorn/worker-split issues show up here
    instead of only in prod.

    `reload` (set by `start-dev`): gunicorn's --reload restarts the web workers
    whenever a Python file changes; templates already reload on every
    request in debug mode (DevelopmentConfig.DEBUG). worker.py is not
    reloaded — restart `start-dev` after changing a job handler.

    Optional (.env), all off by default — nothing changes unless set:
      GUNICORN_BIND_HOST  address to listen on (default 0.0.0.0). Behind
                          nginx (deploy/nginx/), set 127.0.0.1.
      API_PORT            also start a SECOND gunicorn, dedicated to the
                          REST API (/api/…), on this port. nginx routes
                          /api/ to it: an API flood then saturates that
                          process only — the website keeps its own.
                          Only meaningful behind nginx.
      API_GUNICORN_THREADS  threads of the API process (default 8).
      LOG_DIR             write access/error logs to files there
                          (site-*.log, api-*.log) instead of stdout.
    """
    worker_proc = subprocess.Popen(
        [PYTHON, "worker.py"], cwd=ROOT,
        env={**_venv_env(), "FLASKENV": flaskenv},
    )
    _load_launch_env()
    host = os.environ.get("GUNICORN_BIND_HOST", "0.0.0.0").strip() or "0.0.0.0"
    api_port = os.environ.get("API_PORT", "").strip()
    api_proc = None
    try:
        if api_port:
            info(f"API process on {host}:{api_port} (route /api/ to it in nginx)")
            api_proc = subprocess.Popen(
                _gunicorn_cmd(f"{host}:{api_port}", os.environ.get("API_GUNICORN_THREADS", "8"), "api", reload),
                cwd=ROOT, env={**_venv_env(), "FLASKENV": flaskenv},
            )
        threads = os.environ.get("GUNICORN_THREADS", "8")
        run(_gunicorn_cmd(f"{host}:{port}", threads, "site", reload), extra_env={"FLASKENV": flaskenv})
    except KeyboardInterrupt:
        print("\n\033[0;37m  · Server stopped.\033[0m")
    finally:
        for name, proc in (("API process", api_proc), ("background worker process", worker_proc)):
            if proc is not None and proc.poll() is None:
                info(f"Stopping {name}…")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()


def cmd_start_dev() -> None:
    _check_venv()
    port = os.environ.get("FLASK_PORT", "7009")
    url = f"http://{os.environ.get('FLASK_URL', '127.0.0.1')}:{port}"
    header(f"Starting Rulezet v{app_version()} (development)")
    info(f"Serving at {url}")
    info("Debug mode — reloads on code changes (Python and templates)")
    info("Press CTRL+C to stop")
    _run_gunicorn_with_worker("development", port, reload=True)


def cmd_start_prod() -> None:
    _check_venv()

    # 1. Backup
    cmd_backup()

    # 2. Pull + deps + migrations
    header("Updating Rulezet")
    info("Syncing with origin…")
    _sync_with_origin()
    ok("Code updated")

    info("Syncing Git submodules…")
    _sync_submodules()
    ok("Submodules up to date")
    _ensure_pivotick_assets()

    info("Syncing Python dependencies…")
    run([PIP, "install", "-r", "requirements.txt"])
    ok("Dependencies up to date")

    _ensure_ollama()

    info("Running database migrations…")
    run([FLASK, "db", "upgrade"], extra_env={"FLASKENV": "production"})
    ok("Database schema up to date")

    info("Seeding default data (formats, platform-tag configs, AI agent configs)…")
    run([PYTHON, "app.py", "--seed-defaults"], extra_env={"FLASKENV": "production"})
    ok("Default data up to date")

    # 3. Start — same gunicorn+worker.py launch as `start-dev`, see
    # _run_gunicorn_with_worker's docstring for why this isn't `flask run`
    # or an in-process worker.
    _load_launch_env()
    port = os.environ.get("PORT", "80")
    public_url = os.environ.get("INSTANCE_PUBLIC_URL") or f"http://0.0.0.0:{port}"
    header(f"Starting Rulezet v{app_version()} (production)")
    info(f"Serving at {public_url}")
    info("Press CTRL+C to stop")
    _run_gunicorn_with_worker("production", port)


def cmd_restart_prod() -> None:
    """Just step 3 of start-prod: (re)start gunicorn+worker.py in
    production mode — no backup, no git sync, no deps/migrations/seed.
    For when the code is already up to date (or a bad worker.py just needs
    killing and relaunching) and a full start-prod's backup+update pass
    would be redundant/slow."""
    _check_venv()
    _load_launch_env()
    port = os.environ.get("PORT", "80")
    public_url = os.environ.get("INSTANCE_PUBLIC_URL") or f"http://0.0.0.0:{port}"
    header(f"Starting Rulezet v{app_version()} (production, no update)")
    info(f"Serving at {public_url}")
    info("Press CTRL+C to stop")
    _run_gunicorn_with_worker("production", port)


def cmd_test() -> None:
    _check_venv()
    header("Running tests")
    run([PYTEST, "tests"], extra_env={"FLASKENV": "testing"})
    ok("Tests done")


def cmd_backup() -> None:
    header("Backing up database")
    script = ROOT / "backup" / "scripts" / "backup_rulezet.sh"
    if not script.exists():
        error(f"Backup script not found: {script}")
        sys.exit(1)
    run(["bash", str(script)])
    ok("Backup complete")


def cmd_restore() -> None:
    header("Restoring database")
    print("\033[1;31m  WARNING: This will DROP the current database.\033[0m")
    if not _confirm("Are you sure you want to restore?"):
        info("Cancelled.")
        return
    script = ROOT / "backup" / "scripts" / "restore_rulezet.sh"
    if not script.exists():
        error(f"Restore script not found: {script}")
        sys.exit(1)
    # Forward extra args (e.g. a specific dump filename)
    extra = sys.argv[2:]
    run(["bash", str(script)] + extra)


def cmd_update() -> None:
    _check_venv()
    header("Updating Rulezet")

    info("Syncing with origin…")
    _sync_with_origin()
    ok("Code updated")

    info("Syncing Git submodules…")
    _sync_submodules()
    ok("Submodules up to date")
    _ensure_pivotick_assets()
    _check_pivograph_assets()

    info("Syncing Python dependencies…")
    run([PIP, "install", "-r", "requirements.txt"])
    ok("Dependencies up to date")

    _ensure_ollama()

    info("Running database migrations…")
    run([FLASK, "db", "upgrade"], extra_env={"FLASKENV": "development"})
    ok("Database schema up to date")

    info("Seeding default data (formats, platform-tag configs)…")
    run([PYTHON, "app.py", "--seed-defaults"], extra_env={"FLASKENV": "development"})
    ok("Default data up to date")


def cmd_pivotick() -> None:
    """Rebuild the Pivotick graph assets from the pinned submodules (no npm)."""
    header("Building Pivotick graph assets")
    _ensure_pivotick_assets(force=True)
    ok("Done — commit app/static/js/pivotick.iife.js, app/static/css/components/pivotick.css "
       "and app/static/js/pivotick/ together with the submodule bump")


def cmd_pivograph() -> None:
    """Rebuild the Pivograph app (graph view of /rule/formats) from the pinned submodule."""
    header("Building Pivograph")
    try:
        _build_pivograph_assets()
    except Exception as exc:
        error(f"Pivograph build failed: {exc}")
        sys.exit(1)
    ok("Done — commit app/static/pivograph/ together with the submodule bump")


def cmd_deploy() -> None:
    cmd_start_prod()


def cmd_db() -> None:
    """flask db [upgrade|downgrade|migrate …]  — defaults to upgrade."""
    _check_venv()
    sub = sys.argv[2:] if len(sys.argv) > 2 else ["upgrade"]
    run([FLASK, "db"] + sub, extra_env={"FLASKENV": "development"})
    ok(f"flask db {' '.join(sub)} done")


def cmd_db_init() -> None:
    _check_venv()
    header("Initialising database (tables + admin user)")
    run([PYTHON, "app.py", "-i"], extra_env={"FLASKENV": "development"})
    ok("Done")


def cmd_db_reload() -> None:
    _check_venv()
    header("Reloading database (DROP + recreate)")
    print("\033[1;31m  WARNING: This will wipe ALL data.\033[0m")
    if not _confirm("Are you sure you want to wipe and recreate the database?"):
        info("Cancelled.")
        return
    run([PYTHON, "app.py", "-r"], extra_env={"FLASKENV": "development"})
    ok("Database reloaded")


# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS: dict[str, object] = {
    "init":         cmd_init,
    "start-dev":    cmd_start_dev,
    "start":        cmd_start_dev,   # former name, kept so old habits/scripts still work
    "start-prod":   cmd_start_prod,
    "restart-prod": cmd_restart_prod,
    "test":         cmd_test,
    "update":       cmd_update,
    "backup":       cmd_backup,
    "restore":      cmd_restore,
    "deploy":       cmd_deploy,
    "db":           cmd_db,
    "db-init":      cmd_db_init,
    "db-reload":    cmd_db_reload,
    "pivotick":     cmd_pivotick,
    "pivograph":    cmd_pivograph,
    "help":         cmd_help,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        cmd_help()
        sys.exit(0)
    try:
        COMMANDS[sys.argv[1]]()
    except KeyboardInterrupt:
        print("\n\033[0;37m  · Stopped.\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    main()
