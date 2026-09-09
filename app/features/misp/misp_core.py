import os

from flask import json
import requests

from app.core.utils.utils import force_ipv4_resolution

DEFAULT_CTI_TRANSMUTE_URL = "https://cti-transmute.org/api/convert/misp_to_stix"


def convert_misp_to_stix(misp_object: json) -> dict | None:
    """Converts a MISP object to STIX via the cti-transmute.org API (or a
    self-hosted/mirror deployment of it — see CTI_TRANSMUTE_URL below).

    cti-transmute.org publishes both an A and an AAAA record — on a host
    with routable IPv4 but broken/blackholed IPv6 (common on cloud/VPS
    providers), an IPv6 connection attempt doesn't fail fast, it just hangs
    until the timeout below expires, so the whole call times out even
    though the IPv4 address is reachable. Force IPv4-only resolution for
    the duration of this call to route around that.
    """
    url = os.environ.get('CTI_TRANSMUTE_URL') or DEFAULT_CTI_TRANSMUTE_URL
    try:
        with force_ipv4_resolution():
            response = requests.post(
                url,
                json=misp_object,
                headers={"Content-Type": "application/json"},
                timeout=3
            )
        response.raise_for_status()

        return response.json()
    except requests.RequestException as e:
        print(f"Error converting MISP object to STIX: {e}")
        return None
    

