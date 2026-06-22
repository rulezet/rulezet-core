import json
import os
from flask import Blueprint, request as freq
from flask_restx import Api

# -------------------------------------------------------------
# Blueprint: Main API entrypoint
# -------------------------------------------------------------
api_blueprint = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)

# -------------------------------------------------------------
# Load application version
# -------------------------------------------------------------
def version() -> str:
    """Read the application version from the 'version' file."""
    version_file = os.path.join(os.getcwd(), "version")
    with open(version_file, "r") as f:
        return f.readline().strip()


# -------------------------------------------------------------
# Create the main API object
# -------------------------------------------------------------
api = Api(
    api_blueprint,
    title="Rulezet API",
    version=version(),
    description="""
# Welcome to the Rulezet API

The **Rulezet API** provides full programmatic access to your Rulezet instance, including:

- **Rules**: manage detection rules  
- **Bundles**: organize and distribute rule bundles  
- **Account**: manage users and API keys

---

## Access Levels

The API is divided into **public** and **private** namespaces:

### ✅ Public Namespaces
- Free access
- No API key required
- Ideal for retrieving metadata, listing rules, and fetching bundles
- Safe for dashboards, scripts, or external integrations

### 🔑 Private Namespaces
- Require a **personal API key**
- Used for operations that modify data or access sensitive information
- Includes creating, updating, or deleting rules and bundles, managing accounts
- API key can be found in your profile page

---

## Usage
- Public endpoints: accessible directly  
- Private endpoints: include your API key in request headers

Explore all endpoints and try them out using the Swagger UI below.
""",
    doc="/",  # Swagger UI root
)



# -------------------------------------------------------------
# Import all namespaces (organized by module)
# -------------------------------------------------------------

# Rule namespaces
from .rule.rule_public_api import rule_public_ns
from .rule.rule_private_api import rule_private_ns

# Bundle namespaces
from .bundle.bundle_public_api import bundle_public_ns
from .bundle.bundle_private_api import bundle_private_ns

# Account namespaces
from .account.account_public_api import account_public_ns
from .account.account_private_api import account_private_ns


# -------------------------------------------------------------
# Register namespaces in hierarchical paths
# (This produces a clean tree-like structure in Swagger)
# -------------------------------------------------------------

# Rule API

api.add_namespace(rule_public_ns,  path="/rule/public")
api.add_namespace(rule_private_ns, path="/rule/private")

# Bundle API
api.add_namespace(bundle_public_ns,  path="/bundle/public")
api.add_namespace(bundle_private_ns, path="/bundle/private")

# Account API
api.add_namespace(account_public_ns,  path="/account/public")
api.add_namespace(account_private_ns, path="/account/private")

# Sync / Federation API
from .connector.connector_sync_api import sync_ns  # noqa
api.add_namespace(sync_ns, path="/sync")

# Instance registry (phone-home)
from .instance.instance_api import instance_ns  # noqa
api.add_namespace(instance_ns, path="/instance")

# User config / Theme Studio
from .config.config_api import config_ns  # noqa
api.add_namespace(config_ns, path="/config")

# Unified comment thread
from .comment.comment_api import comment_ns  # noqa
api.add_namespace(comment_ns, path="/comments")

# Activity log (admin only)
from .log.log_api import log_ns  # noqa
api.add_namespace(log_ns, path="/log")


# ─── API request audit hook ──────────────────────────────────────────────────

# Paths excluded from API request logging (high-volume or self-referential)
_LOG_SKIP_PREFIXES = ("/api/sync/", "/api/instance/", "/api/log/", "/api/config/",
                      "/api/swaggerui/")

@api_blueprint.after_request
def _log_api_request(response):
    """Log every mutating API call with its HTTP status and JSON result."""
    from contextlib import suppress
    with suppress(Exception):
        path = freq.path
        method = freq.method

        # only mutating verbs; skip swagger UI and internal endpoints
        if method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response
        if any(path.startswith(p) for p in _LOG_SKIP_PREFIXES):
            return response
        # skip swagger static assets
        if path in ("/api/", "/api/swagger.json"):
            return response

        status_code = response.status_code
        level = "success" if status_code < 300 else ("warning" if status_code < 500 else "error")

        # truncate request body
        req_preview = None
        with suppress(Exception):
            body = freq.get_json(silent=True, force=True)
            if body:
                req_preview = json.dumps(body, default=str)[:400]

        # truncate response body
        resp_preview = None
        with suppress(Exception):
            if response.is_json:
                resp_preview = response.get_data(as_text=True)[:400]

        # resolve user from API key or session
        user_id = None
        username = None
        with suppress(Exception):
            from app.core.utils.utils import get_user_from_api
            api_user = get_user_from_api(freq.headers)
            if api_user:
                user_id = api_user.id
                username = api_user.get_username()
        if not user_id:
            with suppress(Exception):
                from flask_login import current_user
                if current_user.is_authenticated:
                    user_id = current_user.id
                    username = current_user.get_username()

        from app.core.utils.activity_log import log_activity
        log_activity(
            "api.request",
            f"{method} {path} → {status_code}",
            category="system",
            level=level,
            title=f"API {method} {path}",
            extra={
                "method":    method,
                "path":      path,
                "status":    status_code,
                "request":   req_preview,
                "response":  resp_preview,
                "user":      username,
            },
            is_public=False,
        )
    return response
