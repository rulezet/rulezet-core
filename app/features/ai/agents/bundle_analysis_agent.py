"""
bundle_analysis_agent.py — BundleAnalysisAgent(AIAgent)

A long, narrative review of a whole bundle, written for the people who will
actually deploy it (SOC analysts, detection engineers, the team lead who has
to say "yes, we run this"). The material it reasons over is assembled by
app/features/bundle/bundle_ai_core.py: identity, composition, per-rule
digest, folder structure, ATT&CK coverage, health checks, community notes,
releases and README-type documents — all real platform data.

Written SECTION BY SECTION, as one growing conversation, instead of one
giant call. On CPU-only Ollama (measured ~5 tok/s prompt reading, ~3.4 tok/s
generation on a 7B model), a single "write 2000 words as JSON" request could
never finish inside any timeout. Here:
  - the bundle material is read once — every later call shares the same
    prompt prefix, so Ollama's prompt cache only processes the new tokens;
  - each section is appended to the conversation (coherent, no repetition);
  - prose is free text (no JSON grammar), streamed with an inactivity
    timeout, one Rulezy step per section;
  - only the short "at a glance" block at the end is structured JSON.
"""
import json

from app.features.ai.ai_core import (
    AgentInvalidResponse,
    AgentResult,
    AIAgent,
    UNTRUSTED_DATA_PREAMBLE,
    strip_control_chars,
)

VERDICTS = {
    'ready':                'Ready to deploy',
    'usable_with_caveats':  'Usable with caveats',
    'needs_work':           'Needs work',
    'not_recommended':      'Not recommended',
}

# (title, what to write, word target). Generated in this order — the
# executive summary is written LAST, once the model has reasoned through
# everything, but displayed first (see DISPLAY_ORDER).
SECTIONS = [
    ("Purpose and threat focus",
     "What problem this bundle solves, the threats and attacker behaviours it targets, the environments it "
     "fits and does not fit. Judge whether the rules actually match what the description promises.", 220),
    ("How the bundle is built",
     "Composition and organisation read as a story: what the mix of formats implies for tooling, where the "
     "rules come from (original work or curation), how navigable the folder structure is, documentation, "
     "rule quality/maturity signals, release discipline.", 260),
    ("Detection coverage and blind spots",
     "What it will realistically catch and what it will miss, grounded in the ATT&CK coverage and the rules "
     "themselves. Distinguish deep coverage from superficial or indicator-only coverage. Name the gaps that "
     "matter most for this bundle's purpose.", 260),
    ("Operational readiness",
     "What happens the day it is deployed: the health-check findings and their real consequences, broken "
     "dependencies, false-positive exposure and tuning effort, marking/TLP concerns, open community notes, "
     "anything in the documents that needs checking before use.", 260),
    ("Deployment guidance",
     "A practical, numbered rollout plan for THIS bundle: which version to deploy, what to enable first, "
     "what to test and tune, what to hold back, what to add alongside it.", 220),
    ("Verdict",
     "Your recommendation and the conditions attached to it, in one or two paragraphs.", 130),
    ("Executive summary",
     "The whole review in ONE tight paragraph a SOC lead can read alone: what it is, who it is for, its "
     "main strength, its main problem, and the verdict.", 150),
]
DISPLAY_ORDER = ["Executive summary", "Purpose and threat focus", "How the bundle is built",
                 "Detection coverage and blind spots", "Operational readiness", "Deployment guidance", "Verdict"]

MIN_SECTION_CHARS = 250
MAX_SECTION_CHARS = 9000   # beyond this: repetition loop

_SYSTEM_PROMPT = """You are a principal detection engineer reviewing a BUNDLE of detection rules \
(a curated ruleset shared on Rulezet, a community platform for YARA, Sigma, Suricata, Zeek, Wazuh… rules). \
Your reader is the team deciding whether and how to deploy it: SOC analysts, detection engineers, a SOC lead. \
Write the review they would want from a trusted senior colleague.

Rules for everything you write:
- INTERPRET, don't inventory. Counts, formats, tags, coverage, health checks, notes and structure are \
evidence: say what they MEAN for someone deploying the bundle. Never paste the data back as long lists.
- Be specific: name a few well-chosen rules, folders, techniques or findings as examples that support a \
point — never enumerate them all.
- Connect the dots (coverage gaps vs. the stated purpose, health errors vs. deployment, sources vs. the \
claimed provenance, releases vs. stability…).
- Be honest and calibrated; missing data (no description, no ATT&CK mapping, no release…) is a finding.
- Ground everything in the material. Never invent threat actors, malware, CVEs, products, versions or numbers.
- Clear professional English, flowing paragraphs; a short list only when it helps the reader act."""


class BundleAnalysisAgent(AIAgent):
    @property
    def key(self):
        return 'bundle_analysis'

    @property
    def display_name(self):
        return 'Bundle Analysis'

    # Same 8k window as the other agents: a different num_ctx makes Ollama
    # reload the model (and a 16k window pushed a 7B model to 12 GB → swap).

    def build_messages(self, *, bundle_context, **kw):
        """The shared conversation prefix — identical for every call of a
        run, so Ollama's prompt cache reads the material only once."""
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": (
                "Here is everything Rulezet knows about the bundle to review.\n\n"
                f"{UNTRUSTED_DATA_PREAMBLE}\n\n"
                "--- BEGIN BUNDLE MATERIAL ---\n"
                f"{bundle_context}\n"
                "--- END BUNDLE MATERIAL ---\n\n"
                "I will ask you for the review one section at a time. For each, reply with the section "
                "body only, in Markdown, without repeating its heading.")},
            {"role": "assistant", "content": "Understood — I have read the material. Ask for the first section."},
        ]

    def json_schema(self):
        string_list = {"type": "array", "items": {"type": "string"}}
        return {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "verdict": {"type": "string", "enum": sorted(VERDICTS)},
                "audience": {"type": "string"},
                "strengths": string_list,
                "risks": string_list,
                "next_steps": string_list,
            },
            "required": ["headline", "verdict", "audience", "strengths", "risks", "next_steps"],
        }

    def execute(self, client, *, acquire_timeout=10, bundle_context='', progress=None, should_stop=None, **kw):
        progress = progress or (lambda stage, text: None)
        messages = self.build_messages(bundle_context=bundle_context)
        per_section_tokens = max(350, min(client.num_predict or 700, 900))
        written = {}

        for i, (title, brief, words) in enumerate(SECTIONS, start=1):
            if should_stop and should_stop():
                raise AgentInvalidResponse("Cancelled.")
            progress('writing', f'Writing “{title}” ({i}/{len(SECTIONS)})…')
            messages.append({"role": "user", "content": (
                f"Section: {title}\n{brief}\nAim for about {words} words. Section body only.")})
            text = client.chat_stream(messages, json_schema=False, acquire_timeout=acquire_timeout,
                                      num_predict=per_section_tokens, should_stop=should_stop)
            text = _clean_section(text, title)
            if len(text) > MAX_SECTION_CHARS:
                raise AgentInvalidResponse(f"Section “{title}” ran away ({len(text)} chars) — likely a repetition loop.")
            messages.append({"role": "assistant", "content": text})
            written[title] = text

        thin = [t for t, v in written.items() if len(v) < MIN_SECTION_CHARS]
        if len(thin) > 2:
            return AgentResult(ok=False, error=f"The model produced almost nothing for: {', '.join(thin)}. "
                                               "Try a larger model.")

        progress('thinking', 'Summing it up — verdict, strengths, risks and next steps…')
        messages.append({"role": "user", "content": (
            "Last step: fill in this JSON object from the review you just wrote. "
            '{"headline": "one sentence, max ~25 words, capturing the bundle and your verdict", '
            '"verdict": "ready|usable_with_caveats|needs_work|not_recommended", '
            '"audience": "one sentence: which team/environment should use it", '
            '"strengths": ["2 to 5 short insights"], "risks": ["2 to 5 short phrases"], '
            '"next_steps": ["2 to 5 short imperative actions"]}')})
        raw = client.chat_stream(messages, json_schema=self.json_schema(), acquire_timeout=acquire_timeout,
                                 num_predict=500, should_stop=should_stop)
        meta = _parse_glance(raw)

        report = "\n\n".join(f"## {t}\n\n{written[t]}" for t in DISPLAY_ORDER if written.get(t))
        return AgentResult(ok=True, content=strip_control_chars(report), meta=meta)

    def parse_response(self, raw):
        # Not used: execute() assembles the result itself.
        return AgentResult(ok=True, content=raw)


def _clean_section(text, title):
    """Strip a repeated heading / stray fences the model sometimes adds."""
    text = strip_control_chars(text or '').strip()
    lines = text.split('\n')
    while lines and (not lines[0].strip() or lines[0].lstrip('#').strip().lower().rstrip(':') == title.lower()):
        lines.pop(0)
    text = '\n'.join(lines).strip()
    if text.startswith('```') and text.endswith('```'):
        text = text.strip('`').strip()
        if text.lower().startswith('markdown'):
            text = text[8:].strip()
    # Demote any "## x" the model wrote inside a section so the TOC stays clean.
    return '\n'.join(('###' + l[2:]) if l.startswith('## ') else l for l in text.split('\n'))


def _parse_glance(raw):
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    def _short_list(key):
        return [strip_control_chars(s).strip()[:300] for s in (data.get(key) or [])
                if isinstance(s, str) and s.strip()][:6]

    verdict = data.get('verdict') if data.get('verdict') in VERDICTS else 'usable_with_caveats'
    return {
        'headline':      strip_control_chars(str(data.get('headline') or '')).strip()[:400],
        'verdict':       verdict,
        'verdict_label': VERDICTS[verdict],
        'audience':      strip_control_chars(str(data.get('audience') or '')).strip()[:400],
        'strengths':     _short_list('strengths'),
        'risks':         _short_list('risks'),
        'next_steps':    _short_list('next_steps'),
    }
