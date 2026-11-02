"""urls.py — web addresses typed by people."""
import re

_HOSTLIKE = re.compile(r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?::\d{1,5})?(?:[/?#][^\s]*)?$', re.I)


def with_scheme(value: str) -> str:
    """'circl.lu' or 'www.circl.lu/team' → 'https://circl.lu' …: an address typed without http(s):// gets https://.
    Anything that has a scheme already, or doesn't look like a host name, is returned as is (and refused later)."""
    value = (value or '').strip()
    if value and '://' not in value and not value.startswith(('/', 'mailto:', 'javascript:', 'data:')) \
            and _HOSTLIKE.match(value.lstrip('/')):
        return 'https://' + value
    return value
