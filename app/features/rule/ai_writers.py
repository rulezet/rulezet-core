"""
ai_writers.py — which AI helped write a rule, for the badge on the rule page: Claude, ChatGPT, Gemini…
(setting rule.ai_writers: names, patterns, logo, colour), read from the rule's author and from the
author / written_with / generated_by / model fields of its own text (YARA meta, Sigma author, Suricata
metadata). Also says "AI" when the rule is declared written with AI (written_with) but names none.
"""
import re

from app.core.utils.app_settings import get_setting

_META_LINE = re.compile(r'(?im)^\s*(?:[$]?\w*?(?:author|written_with|written_by|generated_by|generator|model)\w*)\s*[:=]\s*(.{1,300})$')
_SURICATA_META = re.compile(r'(?i)metadata\s*:([^;]{1,600});')


def _texts(rule) -> list:
    out = [rule.author or '']
    content = (rule.to_string or '')[:20000]
    out += [m.group(1) for m in _META_LINE.finditer(content)]
    for m in _SURICATA_META.finditer(content):
        out += [kv for kv in m.group(1).split(',') if re.search(r'(?i)author|written|generated|model', kv)]
    return out


# A sentence about how something was written — the only place free text (a bundle's description)
# is read: "Claude Code" as the SUBJECT of a bundle must not make it "written with Claude".
_AUTHORSHIP = re.compile(r'(?i)\b(written|drafted|generated|authored|co-?authored|created|made|assisted|produced|with the help of|built)\b')


def detect(rule) -> list:
    """[{key, label, vendor, model, logo, color}] — each AI named once, its most precise model kept."""
    found = _match(' \n '.join(_texts(rule)))
    if not found and getattr(rule, 'written_with', None) in ('ai', 'human_ai'):
        found.append({'key': 'ai', 'label': 'AI', 'vendor': None, 'model': None, 'logo': None, 'color': '#6f42c1'})
    return found


def detect_in_description(text: str) -> list:
    """The AIs a free text says it was written with — only its authorship sentences are read."""
    sentences = re.split(r'(?<=[.!?])\s+|\n+', (text or '')[:20000])
    return _match(' \n '.join(s for s in sentences if _AUTHORSHIP.search(s)))


def _match(text: str) -> list:
    try:
        writers = get_setting('rule.ai_writers') or []
    except KeyError:
        writers = []
    text = (text or '').replace('_', ' ')
    found = []
    for w in writers:
        try:
            if not re.search(w['pattern'], text, re.I):
                continue
            model = None
            if w.get('model'):
                models = [m.group(0).strip() for m in re.finditer(w['model'], text, re.I)]
                model = max(models, key=len) if models else None
            found.append({'key': w['key'], 'label': w['label'], 'vendor': w.get('vendor'), 'model': model,
                          'logo': w.get('logo'), 'color': w.get('color') or '#6c757d'})
        except (re.error, KeyError, TypeError):
            continue
    return found
