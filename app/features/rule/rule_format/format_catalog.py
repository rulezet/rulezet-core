"""Static descriptions of the rule formats Rulezet knows, shown on the public
"Rule formats" page (/rule/formats) and linked from every format chip.

`logo` is a file in static/images/formats/ (the project's own logo, taken
from its official site or GitHub organisation); `icon` is the Font Awesome
fallback when there is none.

Keyed by the lowercase format name stored in Rule.format / FormatRule.name.
A format an admin creates that isn't listed here still appears on the page,
just with a generic description and no official link — add an entry here to
document it.
"""
from app.core.utils.app_settings import setting

FORMAT_CATALOG = setting('formats.catalog')  # app/config/formats.catalog.json


def get_format_info(name: str) -> dict:
    """Catalog entry for a format name, or a generic one for an unknown format."""
    key = (name or "").strip().lower()
    info = FORMAT_CATALOG.get(key)
    if info:
        return dict(info, key=key)
    return {
        "key": key,
        "title": (name or "?").upper(),
        "maintainer": None,
        "category": "Other",
        "icon": "fa-file-code",
        "logo": None,
        "description": "No description for this format yet.",
        "extensions": [],
        "official_url": None,
        "docs_url": None,
    }
