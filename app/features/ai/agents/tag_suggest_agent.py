"""
tag_suggest_agent.py — TagSuggestAgent(AIAgent), 6th AI integration.

Picks the relevant tags for a rule out of a SHORT candidate list found by the
token trie (tag_suggest_core.candidates) — the model never sees the 75k tags
of the database, only ~40 lines, so the call stays small and fast. Every id
it returns that isn't in the list is dropped (no invented tags).
"""
import json

from app.features.ai.ai_core import AgentResult, AIAgent, UNTRUSTED_DATA_PREAMBLE, strip_control_chars
from app.features.ai.tag_suggest_core import format_context

MAX_CONTENT_CHARS = 2500   # the trie already read the whole rule; the model only needs the gist
MAX_AI_CANDIDATES = 25     # the best-scored ones — keeps the prompt small, so the call stays fast
_CONFIDENCES = ('high', 'medium', 'low')

_SYSTEM_PROMPT = """You are a detection engineer tagging a detection rule (YARA, Sigma, Suricata, …) \
on a rule-sharing platform. You get the rule and a numbered list of CANDIDATE tags (MISP taxonomies \
and galaxies) of two kinds: NAME tags, whose name was found in the rule, and GENERIC tags, proposed \
from what rules of this format detect (file type, platform, data source, incident category, \
kill-chain phase) — you also get a short context on the format.

Keep only the candidates that truly describe the rule: the malware family / tool / threat actor it \
detects, the ATT&CK technique it covers, the kind of threat. Drop NAME candidates that only share a \
generic word with the rule, and drop near-duplicates (keep the most specific / the galaxy one). \
Keep a GENERIC tag only when the rule itself clearly supports it (e.g. a PE file tag for a YARA rule \
that checks the MZ header, a network data source for a network signature) — a correct generic tag is \
useful, a doubtful one is not. Never propose a tag that is not in the list.

Respond with ONLY a JSON object:
{"suggestions": [{"id": <candidate id>, "confidence": "high|medium|low", "reason": "<one short sentence citing the rule>"}]}
An empty list is a correct answer when nothing fits."""


def for_model(candidates):
    """What the model sees: the best NAME candidates plus every GENERIC one
    (they score lower than a name found in the title, but the format context
    makes them worth judging)."""
    candidates = list(candidates or ())
    names = [c for c in candidates if not c.get('generic')][:MAX_AI_CANDIDATES]
    return names + [c for c in candidates if c.get('generic')]


class TagSuggestAgent(AIAgent):
    @property
    def key(self):
        return 'tag_suggest'

    @property
    def display_name(self):
        return 'Tag Suggestions'

    def build_messages(self, *, title='', format='', description='', content='', candidates=(), max_suggestions=10, **kw):
        content = (content or '').strip()
        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS] + '\n... (truncated)'
        lines = [f"{c['id']} | {'GENERIC' if c.get('generic') else 'NAME'} | {c['name']}"
                 + (f" ({', '.join(c['matched'][:2])})" if c.get('generic') else '')
                 + (f" — {c['description'][:70]}" if c.get('description') else '')
                 for c in for_model(candidates)]
        ctx = format_context(format)
        user_prompt = (
            f"Keep at most {max_suggestions} tags.\n\n"
            + (f"FORMAT CONTEXT ({format}): {ctx['context']}\n\n" if ctx and ctx['context'] else '')
            + "CANDIDATE TAGS (id | kind | name — description):\n" + '\n'.join(lines) + "\n\n"
            f"{UNTRUSTED_DATA_PREAMBLE}\n\n"
            f"Rule title: {strip_control_chars(title or '(untitled)')}\n"
            f"Rule format: {format or 'unknown'}\n"
            f"Description: {strip_control_chars((description or '(none)')[:600])}\n"
            "--- BEGIN RULE CONTENT ---\n"
            f"{strip_control_chars(content)}\n"
            "--- END RULE CONTENT ---"
        )
        return [{"role": "system", "content": _SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}]

    def json_schema(self):
        return {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "confidence": {"type": "string", "enum": list(_CONFIDENCES)},
                            "reason": {"type": "string"},
                        },
                        "required": ["id", "confidence", "reason"],
                    },
                },
            },
            "required": ["suggestions"],
        }

    def execute(self, client, *, acquire_timeout=10, **kwargs):
        kwargs.pop('progress', None)
        kwargs.pop('should_stop', None)
        allowed = {c['id'] for c in for_model(kwargs.get('candidates'))}
        limit = kwargs.get('max_suggestions') or 10
        if kwargs.pop('simulate', False):
            from app.features.ai.tag_suggest_core import simulate_ai_picks
            picks = simulate_ai_picks(for_model(kwargs.get('candidates')), limit, kwargs.get('format'))
            return AgentResult(ok=True, content=json.dumps(picks), meta={'suggestions': picks},
                               model_used='simulated')
        raw = client.chat(self.build_messages(**kwargs), json_schema=self.json_schema(), acquire_timeout=acquire_timeout)
        result = self.parse_response(raw)
        if result.ok:
            picks, seen = [], set()
            for s in result.meta.get('suggestions', []):
                if s['id'] in allowed and s['id'] not in seen:
                    seen.add(s['id'])
                    picks.append(s)
            result.meta['suggestions'] = picks[:limit]
            result.content = json.dumps(result.meta['suggestions'])
        return result

    def parse_response(self, raw):
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return AgentResult(ok=False, error="Response was not valid JSON.")
        items = data.get('suggestions') if isinstance(data, dict) else None
        if not isinstance(items, list):
            return AgentResult(ok=False, error="Response is missing a 'suggestions' array.")
        out = []
        for s in items:
            if not isinstance(s, dict):
                continue
            try:
                tid = int(s.get('id'))
            except (TypeError, ValueError):
                continue
            conf = s.get('confidence') if s.get('confidence') in _CONFIDENCES else 'medium'
            out.append({'id': tid, 'confidence': conf, 'reason': str(s.get('reason') or '')[:300]})
        return AgentResult(ok=True, content=json.dumps(out), meta={'suggestions': out})
