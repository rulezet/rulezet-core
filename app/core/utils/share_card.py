"""Link previews on social networks / chat apps (LinkedIn, Mastodon, Slack, X, Discord…).

They read the Open Graph / Twitter card tags of the HTML the server sends, without running the
page's Vue, so the card is built here and rendered by base.html (`card` in the template context).
A page without its own card gets the instance's default one. Never build a card for content read
through a private share link: the preview would leak it to the chat app.
"""
import re

from flask import current_app, request, url_for


def _base():
    return (current_app.config.get('INSTANCE_PUBLIC_URL') or request.url_root).rstrip('/')


def plain_text(text, limit=200):
    """Markdown / HTML → a short plain sentence for the preview."""
    raw = re.sub(r'```.*?```', ' ', text or '', flags=re.S)
    raw = re.sub(r'<[^>]+>|!\[[^\]]*\]\([^)]*\)', ' ', raw)
    raw = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', raw)
    raw = re.sub(r'[#>*_`|~]+', ' ', raw)
    raw = ' '.join(raw.split())
    if len(raw) > limit:
        raw = raw[:limit - 3].rsplit(' ', 1)[0] + '…'
    return raw


def share_card(title, description='', path=None, image=None, kind='website', published=None, author=None):
    """The `card` given to a template. `path` defaults to the current page."""
    base = _base()
    image = image or url_for('static', filename='image/rulezet_official_logo.png')
    if image.startswith('/'):
        image = base + image
    elif not image.lower().startswith(('http://', 'https://')):
        image = None
    return {
        'title': title,
        'description': plain_text(description) or 'Community platform for cybersecurity detection rules.',
        'url': base + (path or request.path),
        'image': image,
        'type': kind,
        'published': published.strftime('%Y-%m-%dT%H:%M:%SZ') if published else None,
        'author': author or None,
    }
