"""IP lookup for the admin pages: who an address belongs to and where it comes from.

RDAP (the JSON successor of whois) at the regional registry that holds the
address — found through IANA's bootstrap files, never through a third-party
redirector — plus a reverse DNS lookup. Private / reserved addresses are
answered locally, nothing is sent out for them. Answers are cached
(setting admin.ip_lookup).
"""
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from urllib.parse import urlparse

import requests

from app import cache
from app.core.utils.app_settings import get_setting

USER_AGENT = "Rulezet-IP-lookup"
_REGISTRIES = {          # RDAP host → registry shown in the window
    "rdap.arin.net": "ARIN", "rdap.db.ripe.net": "RIPE NCC", "rdap.apnic.net": "APNIC",
    "rdap.lacnic.net": "LACNIC", "rdap.afrinic.net": "AFRINIC",
}


class LookupError_(Exception):
    """A lookup that can't be done (bad address, registry unreachable)."""


def _config():
    return get_setting("admin.ip_lookup") or {}


def parse_ip(value):
    try:
        return ipaddress.ip_address((value or "").strip().strip("[]"))
    except ValueError:
        raise LookupError_("Not a valid IP address.")


def _scope(ip):
    """'public', or what makes the address non-routable (no lookup then)."""
    if ip.is_loopback:
        return "loopback"
    if ip.is_private:
        return "private"
    if ip.is_link_local:
        return "link-local"
    if ip.is_multicast:
        return "multicast"
    if ip.is_reserved or ip.is_unspecified or not ip.is_global:
        return "reserved"
    return "public"


def _bootstrap(version, cfg, timeout):
    """[(network, rdap_base_url)] from IANA's bootstrap file (cached a week)."""
    key = f"ip_lookup:bootstrap:v{version}"
    services = cache.get(key)
    if services is None:
        url = cfg.get("bootstrap_ipv6" if version == 6 else "bootstrap_ipv4")
        data = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT}).json()
        services = [[prefixes, urls] for prefixes, urls in data.get("services", [])]
        cache.set(key, services, timeout=7 * 24 * 3600)
    found = []
    for prefixes, urls in services:
        https = [u for u in urls if u.startswith("https://")] or urls
        for prefix in prefixes:
            try:
                found.append((ipaddress.ip_network(prefix), https[0]))
            except ValueError:
                continue
    return found


def _rdap_base(ip, cfg, timeout):
    best = None
    for net, url in _bootstrap(ip.version, cfg, timeout):
        if ip in net and (best is None or net.prefixlen > best[0].prefixlen):
            best = (net, url)
    if not best:
        raise LookupError_("No registry is listed for this address.")
    return best[1] if best[1].endswith("/") else best[1] + "/"


def _vcard(entity):
    """{name, kind, email, phone, address} from an RDAP entity's jCard."""
    out = {}
    card = entity.get("vcardArray")
    if not (isinstance(card, list) and len(card) > 1):
        return out
    for item in card[1]:
        if not isinstance(item, list) or len(item) < 4:
            continue
        name, params, value = item[0], item[1] or {}, item[3]
        if name == "fn" and value:
            out["name"] = value
        elif name == "kind":
            out["kind"] = value
        elif name == "email" and "email" not in out:
            out["email"] = value
        elif name == "tel" and "phone" not in out:
            out["phone"] = value if isinstance(value, str) else None
        elif name == "adr":
            label = params.get("label") if isinstance(params, dict) else None
            cc = params.get("cc") if isinstance(params, dict) else None
            if isinstance(cc, str) and len(cc) == 2:
                out["country"] = cc.upper()
            if label:
                out["address"] = " ".join(str(label).split())
                lines = [l.strip() for l in str(label).splitlines() if l.strip()]
                if len(lines) > 1 and not any(ch.isdigit() for ch in lines[-1]):
                    out["country_name"] = lines[-1]      # ARIN: the last line is the country
            elif isinstance(value, list):
                out["address"] = ", ".join(str(v) for v in value if v and not isinstance(v, list))
    return {k: v for k, v in out.items() if v}


def _entities(entities, depth=0):
    """Flat list of {handle, roles, name, email…} — nested entities included (abuse contacts often are)."""
    flat = []
    for e in entities or []:
        if not isinstance(e, dict):
            continue
        flat.append({"handle": e.get("handle"), "roles": e.get("roles") or [], **_vcard(e)})
        if depth < 2:
            flat += _entities(e.get("entities"), depth + 1)
    return flat


def _summarise(data, rdap_url):
    host = urlparse(rdap_url).hostname or ""
    cidrs = []
    for c in data.get("cidr0_cidrs") or []:
        prefix = c.get("v4prefix") or c.get("v6prefix")
        if prefix is not None and c.get("length") is not None:
            cidrs.append(f"{prefix}/{c['length']}")
    if not cidrs and data.get("startAddress") and data.get("endAddress"):
        try:
            cidrs = [str(n) for n in ipaddress.summarize_address_range(
                ipaddress.ip_address(data["startAddress"]), ipaddress.ip_address(data["endAddress"]))][:4]
        except (ValueError, TypeError):
            pass

    contacts = _entities(data.get("entities"))
    def is_maintainer(c):   # RIPE: a maintainer object (MNT-…), not who holds the network
        return str(c.get("handle") or "").upper().startswith("MNT-") or str(c.get("name") or "").upper().startswith("MNT-")

    def first(role, kinds=None):
        return next((c for c in contacts if role in c["roles"] and not is_maintainer(c)
                     and (kinds is None or c.get("kind") in kinds)), None)
    # the organisation holding the network
    owner = (first("registrant", ("org",)) or first("administrative", ("org", "group"))
             or first("registrant") or first("administrative")
             or next((c for c in contacts if not is_maintainer(c)), None))
    abuse = first("abuse")

    events = {e.get("eventAction"): e.get("eventDate") for e in data.get("events") or [] if isinstance(e, dict)}
    description = []
    for r in data.get("remarks") or []:
        description += [d for d in (r.get("description") or []) if isinstance(d, str)]

    return {
        "network": {
            "name": data.get("name"),
            "handle": data.get("handle"),
            "type": data.get("type"),
            "range": f"{data.get('startAddress')} – {data.get('endAddress')}" if data.get("startAddress") else None,
            "cidrs": cidrs,
            "parent": data.get("parentHandle"),
            "status": data.get("status") or [],
        },
        # the network's country, else the one in its owner's postal address (ARIN gives no other)
        "country": ((data.get("country") or "").upper()
                    or (owner or {}).get("country") or (abuse or {}).get("country") or None),
        "country_name": (owner or {}).get("country_name") or (abuse or {}).get("country_name"),
        "owner": owner,
        "abuse": abuse,
        "contacts": [c for c in contacts if c is not owner and c is not abuse][:6],
        "registered": events.get("registration"),
        "updated": events.get("last changed"),
        "description": description[:6],
        "registry": _REGISTRIES.get(host, host),
        "source_url": rdap_url,
    }


def _reverse_dns(ip, timeout):
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(socket.gethostbyaddr, str(ip))
        try:
            return future.result(timeout=timeout)[0]
        except (FutureTimeout, OSError, socket.herror):
            return None


def lookup(value, refresh=False):
    """Everything worth showing about one IP address (dict). Raises LookupError_."""
    ip = parse_ip(value)
    cfg = _config()
    timeout = float(cfg.get("timeout_seconds") or 6)
    links = [{"label": l.get("label"), "url": (l.get("url") or "").replace("{ip}", str(ip))}
             for l in cfg.get("links") or [] if l.get("url")]
    scope = _scope(ip)
    base = {"ip": str(ip), "version": ip.version, "scope": scope, "links": links}
    if scope != "public":
        return {**base, "message": f"A {scope} address: it is not routed on the Internet, "
                                   f"there is nothing to look up."}

    key = f"ip_lookup:{ip}"
    if not refresh:
        hit = cache.get(key)
        if hit:
            return {**hit, "links": links, "cached": True}

    rdap_url = _rdap_base(ip, cfg, timeout) + f"ip/{ip}"
    try:
        resp = requests.get(rdap_url, timeout=timeout,
                            headers={"Accept": "application/rdap+json", "User-Agent": USER_AGENT})
    except requests.RequestException:
        raise LookupError_("The registry did not answer — try again later.")
    if resp.status_code == 404:
        raise LookupError_("The registry has no record for this address.")
    if resp.status_code == 429:
        raise LookupError_("The registry is rate-limiting lookups — try again in a minute.")
    if not resp.ok:
        raise LookupError_(f"The registry answered with an error ({resp.status_code}).")
    try:
        data = resp.json()
    except ValueError:
        raise LookupError_("The registry's answer could not be read.")

    result = {**base, **_summarise(data, resp.url or rdap_url)}
    if cfg.get("reverse_dns", True):
        result["hostname"] = _reverse_dns(ip, min(timeout, 3))
    cache.set(key, result, timeout=int(float(cfg.get("cache_hours") or 24) * 3600))
    return {**result, "cached": False}
