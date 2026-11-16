"""
tag_suggest_agent.py — TagSuggestAgent(AIAgent), 6th AI integration.

Picks the relevant tags for a rule out of a SHORT candidate list found by the
token trie (tag_suggest_core.candidates) — the model never sees the 75k tags
of the database, only ~40 lines, so the call stays small and fast. Every id
it returns that isn't in the list is dropped (no invented tags).
"""
import json

from app.features.ai.ai_core import AgentResult, AIAgent, UNTRUSTED_DATA_PREAMBLE, strip_control_chars

MAX_CONTENT_CHARS = 2500   # the trie already read the whole rule; the model only needs the gist
MAX_AI_CANDIDATES = 25     # the best-scored ones — keeps the prompt small, so the call stays fast
_CONFIDENCES = ('high', 'medium', 'low')

_SYSTEM_PROMPT = """You are a detection engineer tagging a detection rule (YARA, Sigma, Suricata, …) \
on a rule-sharing platform. You get the rule and a numbered list of CANDIDATE tags (MISP taxonomies \
and galaxies) that matched words of the rule.

Keep only the candidates that truly describe the rule: the malware family / tool / threat actor it \
detects, the ATT&CK technique it covers, the kind of threat. Drop candidates that only share a \
generic word with the rule, and drop near-duplicates (keep the most specific / the galaxy one). \
Never propose a tag that is not in the list.

Respond with ONLY a JSON object:
{"suggestions": [{"id": <candidate id>, "confidence": "high|medium|low", "reason": "<one short sentence citing the rule>"}]}
An empty list is a correct answer when nothing fits."""


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
        lines = [f"{c['id']} | {c['name']}" + (f" — {c['description'][:70]}" if c.get('description') else '')
                 for c in list(candidates)[:MAX_AI_CANDIDATES]]
        user_prompt = (
            f"Keep at most {max_suggestions} tags.\n\n"
            "CANDIDATE TAGS (id | name — description):\n" + '\n'.join(lines) + "\n\n"
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
        allowed = {c['id'] for c in list(kwargs.get('candidates') or ())[:MAX_AI_CANDIDATES]}
        limit = kwargs.get('max_suggestions') or 10
        if kwargs.pop('simulate', False):
            from app.features.ai.tag_suggest_core import simulate_ai_picks
            picks = simulate_ai_picks(list(kwargs.get('candidates') or ())[:MAX_AI_CANDIDATES], limit)
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
