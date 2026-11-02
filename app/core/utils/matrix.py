"""
matrix.py — post a message in a Matrix room (.env: MATRIX_HOMESERVER, MATRIX_ACCESS_TOKEN, MATRIX_ROOM_ID; set on
Admin → Settings → Configuration). manage.py start-prod uses the same three keys to say "updating / back online".
Standard library only; never raises.

    send(text, html=None) -> (ok, error)
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request


def settings() -> dict:
    from app.features.admin.admin_core import read_env_file
    env = read_env_file()
    return {k: env.get(k) or os.environ.get(k) or '' for k in ('MATRIX_HOMESERVER', 'MATRIX_ACCESS_TOKEN', 'MATRIX_ROOM_ID')}


def send(text: str, html: str | None = None) -> tuple[bool, str]:
    s = settings()
    server, token, room = s['MATRIX_HOMESERVER'], s['MATRIX_ACCESS_TOKEN'], s['MATRIX_ROOM_ID']
    if not (server and token and room):
        return False, 'Set the homeserver, the access token and the room first.'
    if not server.startswith(('https://', 'http://')):
        return False, 'The homeserver must be an address like https://matrix.org.'
    body = {'msgtype': 'm.notice', 'body': text}
    if html:
        body.update({'format': 'org.matrix.custom.html', 'formatted_body': html})
    url = (f"{server.rstrip('/')}/_matrix/client/v3/rooms/{urllib.parse.quote(room, safe='')}"
           f"/send/m.room.message/rulezet-{int(time.time() * 1000)}")
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method='PUT',
                                 headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=10).read()
        return True, ''
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read() or b'{}').get('error') or ''
        except Exception:
            detail = ''
        return False, f'Matrix answered {e.code}' + (f': {detail}' if detail else '') + \
            (' — is the bot invited to the room?' if e.code == 403 else ' — check the access token.' if e.code == 401 else '')
    except Exception as e:
        return False, f'Could not reach the homeserver ({type(e).__name__}).'
