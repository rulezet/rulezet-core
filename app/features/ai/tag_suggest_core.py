"""
tag_suggest_core.py — fast tag candidates for a rule (6th AI integration).

Step 1, no AI, a few milliseconds: a token trie built once in memory from the
tags of the families listed in the setting `ai.tag_suggest` (taxonomy /
galaxy namespaces worth matching on a detection rule) plus the tags already
in real use. Each tag gives its terms — the value of its name
(`misp-galaxy:tool="Mimikatz"` -> "mimikatz"), its galaxy synonyms, the
ATT&CK id in its name — and the rule's text is walked through the trie.
Matches are scored by rarity (a term shared by 200 tags is worth little),
length (multi-word phrases beat single words) and where they were found (the
title counts double).

Step 2 (tag_suggest_agent.py) hands only these candidates to the model,
which picks and explains; anything it names outside the list is dropped.

The trie is rebuilt when the tag table or the setting changes (checked at
most every CHECK_EVERY_S seconds per worker).
"""
import re
import threading
import time
from collections import defaultdict

from sqlalchemy import func

from app import db
from app.core.db_class.tag import RuleTagAssociation, Tag
from app.core.utils.app_settings import get_setting

CHECK_EVERY_S = 60
MAX_PHRASE_TOKENS = 6
MAX_TEXT_CHARS = 30000
_END = '\0'  # trie node key holding the tag ids ending there

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")
_ATTACK_ID_RE = re.compile(r"\bT\d{4}(?:\.\d{3})?\b", re.I)

_lock = threading.Lock()
_index = {'stamp': None, 'checked': 0.0, 'trie': {}, 'term_tags': {}, 'tags': {}}


def _settings():
    value = get_setting('ai.tag_suggest') or {}
    value = dict(value) if isinstance(value, dict) else {}
    return {
        'families': set(value.get('families') or []),
        'include_used_min_rules': int(value.get('include_used_min_rules') or 0),
        'exclude_prefixes': tuple(p.lower() for p in (value.get('exclude_prefixes') or [])),
        'min_term_length': int(value.get('min_term_length') or 4),
        'stopwords': {s.lower() for s in (value.get('stopwords') or [])},
        'max_candidates': int(value.get('max_candidates') or 40),
        'max_ai_suggestions': int(value.get('max_ai_suggestions') or 10),
        'simulate_ai': bool(value.get('simulate_ai')),
    }


def tokenize(text):
    return _TOKEN_RE.findall((text or '').lower())


def _tag_terms(tag, min_len, stopwords):
    """The phrases (token tuples) a tag is found by."""
    name = tag.name or ''
    raw = []
    # misp-galaxy:tool="Mimikatz" / ms-caro-malware:malware-type="Trojan" / tlp:clear / plain
    m = re.search(r'="([^"]+)"', name)
    if m:
        raw.append(m.group(1))
    elif ':' in name:
        raw.append(name.split(':', 1)[1])
    else:
        raw.append(name.replace('_', ' '))
    meta = tag.galaxy_meta if isinstance(tag.galaxy_meta, dict) else {}
    for syn in (meta.get('synonyms') or [])[:30]:
        if isinstance(syn, str):
            raw.append(syn)
    terms = set()
    for value in raw:
        # "Command and Scripting Interpreter - T1059" -> both halves
        for part in re.split(r"\s+-\s+", value):
            toks = tuple(tokenize(part))
            if not toks or len(toks) > MAX_PHRASE_TOKENS:
                continue
            if len(toks) == 1:
                t = toks[0]
                if len(t) < min_len or t in stopwords or t.isdigit():
                    continue
            terms.add(toks)
    for tid in _ATTACK_ID_RE.findall(name):
        terms.add((tid.lower(),))
    return terms


def _stamp(cfg):
    count, last = db.session.query(func.count(Tag.id), func.max(Tag.updated_at)).one()
    return (count, str(last), hash(repr(sorted(cfg['families']))), cfg['include_used_min_rules'],
            cfg['min_term_length'], hash(repr(sorted(cfg['stopwords']))), cfg['exclude_prefixes'])


def _build(cfg):
    used_ids = set()
    if cfg['include_used_min_rules'] > 0:
        used_ids = {tid for (tid,) in db.session.query(RuleTagAssociation.tag_id)
                    .group_by(RuleTagAssociation.tag_id)
                    .having(func.count(RuleTagAssociation.rule_id) >= cfg['include_used_min_rules'])}
    q = Tag.query.filter(Tag.is_active.is_(True))
    cond = Tag.namespace.in_(cfg['families']) if cfg['families'] else None
    if used_ids:
        cond = Tag.id.in_(used_ids) if cond is None else (cond | Tag.id.in_(used_ids))
    if cond is None:
        return {}, {}, {}
    trie, term_tags, tags = {}, defaultdict(set), {}
    for tag in q.filter(cond).with_entities(Tag.id, Tag.name, Tag.description, Tag.namespace,
                                            Tag.galaxy_meta, Tag.color, Tag.icon, Tag.source).yield_per(2000):
        if cfg['exclude_prefixes'] and (tag.name or '').lower().startswith(cfg['exclude_prefixes']):
            continue
        terms = _tag_terms(tag, cfg['min_term_length'], cfg['stopwords'])
        if not terms:
            continue
        tags[tag.id] = {'id': tag.id, 'name': tag.name, 'description': (tag.description or '')[:300],
                        'namespace': tag.namespace, 'color': tag.color, 'icon': tag.icon, 'source': tag.source}
        for toks in terms:
            node = trie
            for t in toks:
                node = node.setdefault(t, {})
            node.setdefault(_END, set()).add(tag.id)
            term_tags[toks].add(tag.id)
    return trie, {k: len(v) for k, v in term_tags.items()}, tags


def get_index():
    """The live trie, rebuilt when tags or the setting changed."""
    now = time.monotonic()
    if _index['stamp'] is not None and now - _index['checked'] < CHECK_EVERY_S:
        return _index
    with _lock:
        if _index['stamp'] is not None and now - _index['checked'] < CHECK_EVERY_S:
            return _index
        cfg = _settings()
        stamp = _stamp(cfg)
        if stamp != _index['stamp']:
            trie, term_df, tags = _build(cfg)
            _index.update(trie=trie, term_tags=term_df, tags=tags, stamp=stamp)
        _index['checked'] = now
    return _index


def _walk(trie, tokens):
    """Every (phrase, tag ids) of the trie found in the token stream."""
    found = []
    n = len(tokens)
    for i in range(n):
        node = trie
        for j in range(i, min(n, i + MAX_PHRASE_TOKENS)):
            node = node.get(tokens[j])
            if node is None:
                break
            if _END in node:
                found.append((tuple(tokens[i:j + 1]), node[_END]))
    return found


def candidates(*, title='', description='', content='', exclude_ids=(), limit=None, **_ignored):
    """Ranked tag candidates for this rule text: [{...tag, score, matched}]."""
    cfg = _settings()
    idx = get_index()
    trie, term_df, tags = idx['trie'], idx['term_tags'], idx['tags']
    if not trie:
        return []
    exclude = set(exclude_ids or ())
    scores, matched = defaultdict(float), defaultdict(set)
    for weight, text in ((2.0, title), (1.0, description), (1.0, (content or '')[:MAX_TEXT_CHARS])):
        seen = set()
        for phrase, tag_ids in _walk(trie, tokenize(text)):
            if phrase in seen:          # a word repeated 50 times in the content counts once per field
                continue
            seen.add(phrase)
            value = weight * len(phrase) / max(1, term_df.get(phrase, 1)) ** 0.5
            for tid in tag_ids:
                if tid in exclude:
                    continue
                scores[tid] += value
                matched[tid].add(' '.join(phrase))
    ranked = sorted(scores, key=lambda t: (-scores[t], tags[t]['name']))[:limit or cfg['max_candidates']]
    return [{**tags[t], 'score': round(scores[t], 3), 'matched': sorted(matched[t])} for t in ranked]


def simulate_ai_picks(found, max_suggestions):
    """What the model is asked to do, done from the trie scores — setting
    simulate_ai (dev machine with a slow local Ollama). Keeps the clearly
    leading candidates, one tag per set of matched words (a galaxy / taxonomy
    tag rather than its plain twin), with a reason naming the words."""
    if not found:
        return []
    top = found[0]['score'] or 1
    picks, seen_terms = [], set()
    for c in sorted(found, key=lambda c: (-c['score'], c['namespace'] == '')):
        if c['score'] < top * 0.35 or len(picks) >= max_suggestions:
            break
        terms = tuple(c['matched'])
        if terms in seen_terms:
            continue
        seen_terms.add(terms)
        ratio = c['score'] / top
        picks.append({'id': c['id'], 'confidence': 'high' if ratio >= .7 else 'medium' if ratio >= .45 else 'low',
                      'reason': '[simulated] The rule mentions ' + ', '.join(f'"{t}"' for t in terms[:3]) + '.'})
    return picks


def can_use(user) -> bool:
    """Who sees and uses Tag Suggestions — trie AND AI step: admins, AI
    Operators (ai.use) and AI Managers (ai.manage), while the agent is enabled
    (AI admin → Tag Suggestions / Overview). Plain users never see it. Every
    route and template goes through this one check. On the rule edit page this
    includes a Tag manager (rule.tag_any) who is also an AI Operator, in the
    tags-only restricted edit of someone else's rule."""
    from app.core.db_class.ai import AIAgentConfig
    if not user or not user.is_authenticated:
        return False
    if not (user.is_admin() or user.has_permission('ai.use') or user.has_permission('ai.manage')):
        return False
    cfg = AIAgentConfig.query.filter_by(agent_key='tag_suggest').first()
    return cfg.enabled if cfg else True


ai_available = can_use   # the AI step has the same audience as the trie


def bundle_text(bundle, max_rules=300):
    """What a bundle is about, as text for the trie: its name and description,
    plus the titles and tag names of its (non-deleted) rules — a tag already
    used by several of its rules is a strong hint for the bundle itself."""
    from app.core.db_class.bundle import BundleRuleAssociation
    from app.core.db_class.rule import Rule
    rows = (db.session.query(Rule.id, Rule.title)
            .join(BundleRuleAssociation, BundleRuleAssociation.rule_id == Rule.id)
            .filter(BundleRuleAssociation.bundle_id == bundle.id, Rule.is_deleted.is_(False))
            .limit(max_rules).all())
    rule_ids = [r.id for r in rows]
    tag_names = []
    if rule_ids:
        tag_names = [n for (n,) in db.session.query(Tag.name)
                     .join(RuleTagAssociation, RuleTagAssociation.tag_id == Tag.id)
                     .filter(RuleTagAssociation.rule_id.in_(rule_ids))]
    content = '\n'.join([r.title or '' for r in rows] + [n.replace('_', ' ') for n in tag_names])
    return {'title': bundle.name or '', 'description': bundle.description or '',
            'content': content, 'format': 'bundle'}


def ai_pick(user, text, exclude, target_type, target_id):
    """Runs the AI step for a rule or a bundle: trie candidates -> agent ->
    history row. Returns (json body, http status)."""
    from app.features.ai.ai_core import get_agent
    found = candidates(exclude_ids=exclude, **text)
    if not found:
        return {"ok": True, "suggestions": []}, 200
    cfg = _settings()
    result = get_agent('tag_suggest').run(
        user=user, rule_id=target_id if target_type == 'rule' else None,
        input_summary=text['title'] or text['content'][:200],
        candidates=found, max_suggestions=cfg['max_ai_suggestions'], simulate=cfg['simulate_ai'], **text,
    )
    if not result.ok:
        return {"ok": False, "error": result.error or "The AI call failed."}, 502
    by_id = {c['id']: c for c in found}
    picks = [{**by_id[s['id']], 'confidence': s['confidence'], 'reason': s['reason']}
             for s in result.meta.get('suggestions', [])]
    _save_history(user, text, target_type, target_id, found, picks, result.model_used)
    return {"ok": True, "model": result.model_used, "simulated": cfg['simulate_ai'], "suggestions": picks}, 200


def _save_history(user, text, target_type, target_id, found, picks, model):
    """One AIGeneration row per AI call — the admin page's history table
    (/ai/admin/tag-suggest), like the other agents."""
    import uuid as uuid_mod
    from app.core.db_class.ai import AIGeneration
    noun = 'Bundle' if target_type == 'bundle' else 'Rule'
    lines = [f"**{noun}:** {text['title'] or '(untitled)'}" + (f" ({text['format']})" if target_type == 'rule' else ''), "",
             f"**AI picks** ({len(picks)} of {len(found)} candidates):", ""]
    lines += [f"- `{p['name']}` — {p['confidence']}: {p['reason']}" for p in picks] or ["- none"]
    lines += ["", "**Candidates from the trie:** " + ', '.join(f"`{c['name']}`" for c in found)]
    try:
        db.session.add(AIGeneration(
            uuid=str(uuid_mod.uuid4()), agent_key='tag_suggest',
            rule_id=target_id if target_type == 'rule' else None,
            bundle_id=target_id if target_type == 'bundle' else None,
            user_id=user.id, content='\n'.join(lines), model=model,
            meta={'target': target_type,
                  'suggestions': [{'id': p['id'], 'name': p['name'], 'confidence': p['confidence'],
                                   'reason': p['reason']} for p in picks],
                  'candidates': [c['name'] for c in found]},
            is_public=False,
        ))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[tag_suggest] history not saved: {e}")


def index_stats():
    idx = get_index()
    return {'tags': len(idx['tags']), 'terms': len(idx['term_tags'])}
