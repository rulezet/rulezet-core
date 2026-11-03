"""
official_instance.py — is this the official Rulezet (rulezet.org)?

Decided by the address the instance is served at: only rulezet.org is the official instance, and nobody
else can be served at that domain. A copy that sets IS_OFFICIAL_INSTANCE=true in its .env does NOT become
official (the variable is only read by the tests). What depends on it: accepting the 24 h pings of the other
instances (/api/instance/register), the admin "Instances" page, and search engine indexing (setting seo).
"""
from urllib.parse import urlparse

from flask import current_app, has_request_context, request

OFFICIAL_HOSTS = ('rulezet.org', 'www.rulezet.org')


def is_official_instance() -> bool:
    if current_app.config.get('TESTING'):
        return bool(current_app.config.get('IS_OFFICIAL_INSTANCE'))     # the tests switch it on and off
    if has_request_context():
        host = (request.host or '').split(':')[0].lower()
    else:                                                                  # background work: the public URL
        host = (urlparse(current_app.config.get('INSTANCE_PUBLIC_URL') or '').hostname or '').lower()
    return host in OFFICIAL_HOSTS
