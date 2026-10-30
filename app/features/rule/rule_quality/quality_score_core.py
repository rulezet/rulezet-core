"""
quality_score_core.py — objective per-rule quality scoring.

Deliberately separate from votes/favorites/comments ("engagement"): a rule's
quality_score answers "is this well documented, traceable and valid?"
regardless of how popular it is. Engagement is folded in only as a capped
bonus on top, never mixed into the base score, so filtering/sorting by
quality_score alone finds "well-formed but unpopular" and "popular but
undocumented" rules correctly.

quality_score is NULL until a rule has actually been analyzed (either via a
write-time hook or the 'compute_rule_quality_score' background job) — distinct
from a real low score of 0.
"""
import datetime
import math
from typing import Any, Dict, Tuple

from app import db
from app.core.db_class.attack import RuleAttackAssociation
from app.core.db_class.rule import RuleUpdateHistory
from app.core.db_class.tag import RuleTagAssociation, Tag
from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType, load_all_rule_formats

_PLACEHOLDER_VALUES = {"", "unknown", "n/a", "none", "null", "no description provided"}
_DEFAULT_TAG_PREFIXES = ("tlp:", "pap:")

# ATT&CK mapping is idiomatic for these formats on this platform; scoring it
# as a missing criterion for e.g. YARA would unfairly penalize a format that
# was never expected to carry ATT&CK tags in the first place.
_ATTACK_APPLICABLE_FORMATS = {"sigma", "suricata", "zeek", "wazuh"}

# A rule edited well after its own creation has had at least one real review
# pass. The two timestamps can differ by a few seconds/ms even on a rule
# that was never touched again (two separate now() calls at creation time),
# so a small threshold avoids counting that as "reviewed".
_FRESHNESS_THRESHOLD = datetime.timedelta(hours=1)


def _is_meaningful(value: Any) -> bool:
    if not value:
        return False
    return str(value).strip().lower() not in _PLACEHOLDER_VALUES


# Format string -> RuleType instance (or None for an unknown format). Building
# this involves load_all_rule_formats() (a pkgutil scan) plus instantiating
# every RuleType subclass just to read its .format — cheap once, but scoring
# thousands of rules called it fresh per rule, which measurably added up.
# Module-level so it also stays warm across job runs in the worker process.
_rule_type_instances: Dict[str, Any] = {}
_formats_loaded = False


def _get_rule_type_instance(rule_format: str):
    global _formats_loaded
    fmt = (rule_format or "").lower()
    if fmt in _rule_type_instances:
        return _rule_type_instances[fmt]
    if not _formats_loaded:
        load_all_rule_formats()
        _formats_loaded = True
    instance = None
    for subclass in RuleType.__subclasses__():
        candidate = subclass()
        if candidate.format.lower() == fmt:
            instance = candidate
            break
    _rule_type_instances[fmt] = instance
    return instance


def _weighted(checks: Dict[str, bool], weights: Dict[str, float]) -> Tuple[float, float]:
    earned = sum(weights[k] for k, v in checks.items() if v and k in weights)
    total = sum(weights.values())
    return earned, total


def _score_traceability(rule) -> Tuple[float, float, Dict[str, bool]]:
    checks = {
        "has_original_uuid": _is_meaningful(rule.original_uuid),
        "has_github_path": _is_meaningful(rule.github_path),
        "has_source": _is_meaningful(rule.source),
    }
    weights = {"has_original_uuid": 10, "has_github_path": 5, "has_source": 5}
    earned, total = _weighted(checks, weights)
    return earned, total, checks


def _meaningful_tag_count(rule_id: int) -> int:
    """Tags beyond the auto-attached tlp:/pap: defaults — a context-free query
    (no current_user dependency) so this is safe from background-job threads
    that have no request/session context, unlike get_tags_for_rule()."""
    names = [
        name for (name,) in db.session.query(Tag.name)
        .join(RuleTagAssociation, RuleTagAssociation.tag_id == Tag.id)
        .filter(RuleTagAssociation.rule_id == rule_id)
        .all()
    ]
    return sum(1 for n in names if not str(n).lower().startswith(_DEFAULT_TAG_PREFIXES))


def _score_documentation(rule) -> Tuple[float, float, Dict[str, bool]]:
    """Basic human-readable authorship info — separate from _score_metadata's
    structured triage fields (references, falsepositives, level, tags, ATT&CK)."""
    checks = {
        "has_description": _is_meaningful(rule.description) and len(str(rule.description).strip()) >= 30,
        "has_author": _is_meaningful(rule.author),
        "has_license": _is_meaningful(rule.license),
        "says_how_written": bool(getattr(rule, 'written_with', None)),   # human / AI / both — transparency
    }
    weights = {"has_description": 10, "has_author": 5, "has_license": 5, "says_how_written": 5}
    earned, total = _weighted(checks, weights)
    return earned, total, checks


def _score_metadata(rule, rule_type, batch_context=None) -> Tuple[float, float, Dict[str, bool]]:
    """Structured triage metadata — the fields a SOC analyst actually leans on
    at alert time (references, known false-positive scenarios, severity
    level, taxonomy tags, ATT&CK mapping), as opposed to _score_documentation's
    free-text authorship fields."""
    if batch_context is not None:
        has_tags = rule.id in batch_context["meaningful_tags"]
    else:
        has_tags = _meaningful_tag_count(rule.id) > 0

    checks: Dict[str, bool] = {"has_meaningful_tags": has_tags}
    weights: Dict[str, float] = {"has_meaningful_tags": 5}

    if (rule.format or "").lower() in _ATTACK_APPLICABLE_FORMATS:
        if batch_context is not None:
            has_attack = rule.id in batch_context["has_attack"]
        else:
            has_attack = db.session.query(RuleAttackAssociation.id).filter_by(rule_id=rule.id).first() is not None
        checks["has_attack_mapping"] = has_attack
        weights["has_attack_mapping"] = 5

    earned, total = _weighted(checks, weights)

    # Per-format metadata checklist (references, falsepositives, level, meta
    # block richness, ...) — averaged into a single 10pt bucket so a format
    # with 4 signals and one with 2 both max out at 10, not 40/20.
    format_signals: Dict[str, bool] = {}
    if rule_type is not None and rule.to_string:
        try:
            format_signals = rule_type.documentation_signals(rule.to_string) or {}
        except Exception:
            format_signals = {}
    if format_signals:
        signal_ratio = sum(1 for v in format_signals.values() if v) / len(format_signals)
        earned += signal_ratio * 10
        total += 10
        checks.update({f"format:{k}": v for k, v in format_signals.items()})

    return earned, total, checks


def _score_validity(rule, rule_type, batch_context=None) -> Tuple[float, float, Dict[str, bool]]:
    is_valid = False
    if rule_type is not None and rule.to_string:
        try:
            is_valid = bool(rule_type.validate(rule.to_string).ok)
        except Exception:
            is_valid = False

    if batch_context is not None:
        no_pending_failure = rule.id not in batch_context["last_history_failed"]
    else:
        last_history = (
            RuleUpdateHistory.query
            .filter_by(rule_id=rule.id)
            .order_by(RuleUpdateHistory.analyzed_at.desc())
            .first()
        )
        no_pending_failure = not (last_history is not None and last_history.success is False)

    checks = {
        "passes_validation": is_valid,
        "no_pending_failed_update": no_pending_failure,
    }
    weights = {"passes_validation": 15, "no_pending_failed_update": 10}
    earned, total = _weighted(checks, weights)
    return earned, total, checks


def _content_hash(text):
    import hashlib
    return hashlib.sha256((text or '').encode('utf-8', 'replace')).hexdigest()


def _score_review(rule, batch_context=None) -> Tuple[float, float, Dict[str, bool]]:
    """Has it been looked at? A review (Review button on the rule page — the owner or an admin)
    on the CURRENT content; an edit well after creation still counts as a first look."""
    current = _content_hash(rule.to_string)
    if batch_context is not None:
        reviews = batch_context["reviews"].get(rule.id, [])
    else:
        from app.core.db_class.rule import RuleReview
        reviews = [(r.user_id, r.verdict, r.content_hash)
                   for r in RuleReview.query.filter_by(rule_id=rule.id).all()]
    others = reviews
    on_current = [r for r in reviews if r[2] == current]
    edited_later = bool(rule.creation_date and rule.last_modif
                        and (rule.last_modif - rule.creation_date) > _FRESHNESS_THRESHOLD)
    checks = {
        "reviewed_since_creation": bool(others) or edited_later,
        "approved_by_reviewer": any(r[1] == "approved" for r in on_current),
        "approved_by_two_reviewers": len({r[0] for r in on_current if r[1] == "approved"}) >= 2,
        "no_changes_requested": not any(r[1] == "changes_requested" for r in on_current),
    }
    weights = {"reviewed_since_creation": 5, "approved_by_reviewer": 10,
               "approved_by_two_reviewers": 5, "no_changes_requested": 5}
    earned, total = _weighted(checks, weights)
    return earned, total, checks


DUPLICATE_SIMILARITY = 0.95   # similarity (0-1) from which an OLDER rule makes this one a duplicate


def _score_usage(rule, batch_context=None) -> Tuple[float, float, Dict[str, bool]]:
    """Uniqueness and use: not a near-copy of an older rule (similarity results), picked into a
    bundle, linked to a threat (CVE or ATT&CK). The older of two near-identical rules keeps its points."""
    if batch_context is not None:
        duplicate = rule.id in batch_context["duplicates"]
        in_bundle = rule.id in batch_context["in_bundle"]
        has_attack = rule.id in batch_context["has_attack"]
        has_ai = rule.id in batch_context["ai_analysis"]
    else:
        from app.core.db_class.bundle import BundleRuleAssociation
        from app.core.db_class.rule import Rule
        from app.core.db_class.similarity import RuleSimilarity
        duplicate = db.session.query(RuleSimilarity.id).join(Rule, Rule.id == RuleSimilarity.similar_rule_id).filter(
            RuleSimilarity.rule_id == rule.id, RuleSimilarity.score >= DUPLICATE_SIMILARITY,
            Rule.is_deleted == False, Rule.creation_date < rule.creation_date).first() is not None   # noqa: E712
        in_bundle = db.session.query(BundleRuleAssociation.id).filter_by(rule_id=rule.id).first() is not None
        has_attack = db.session.query(RuleAttackAssociation.id).filter_by(rule_id=rule.id).first() is not None
        from app.core.db_class.ai import AIGeneration
        has_ai = db.session.query(AIGeneration.id).filter_by(agent_key='rule_analysis', rule_id=rule.id,
                                                             is_public=True).first() is not None
    has_cve = bool(rule.cve_id and str(rule.cve_id).strip() not in ('', '[]', 'null'))
    checks = {
        "not_a_duplicate": not duplicate,
        "used_in_a_bundle": in_bundle,
        "linked_to_a_threat": has_cve or has_attack,
        "has_ai_analysis": has_ai,              # a published report of the AI analysis agent
    }
    weights = {"not_a_duplicate": 10, "used_in_a_bundle": 5, "linked_to_a_threat": 5, "has_ai_analysis": 5}
    earned, total = _weighted(checks, weights)
    return earned, total, checks


def _score_field_reports(rule, batch_context=None):
    """Scopes users declared on the rule ("works for me — linux, Suricata 7…" / "doesn't work"):
    reported working somewhere earns points, a report that it doesn't work costs them back.
    Not counted (None) while nobody declared a scope."""
    if batch_context is not None:
        works, broken = batch_context["scopes"].get(rule.id, (0, 0))
    else:
        from app.core.db_class.rule import RuleScope
        rows = db.session.query(RuleScope.works).filter_by(rule_id=rule.id).all()
        works, broken = sum(1 for (w,) in rows if w), sum(1 for (w,) in rows if not w)
    if not works and not broken:
        return None
    checks = {
        "works_somewhere": works > 0,
        "works_in_several_places": works >= 2,
        "no_report_it_fails": broken == 0,
    }
    weights = {"works_somewhere": 10, "works_in_several_places": 5, "no_report_it_fails": 10}
    earned, total = _weighted(checks, weights)
    return earned, total, checks


def _score_testing(rule, batch_context=None):
    """Run on sample sets (rule tester) for the current content: does it detect its samples, and
    no false positive? Not counted at all (None) while the rule was never tested — an instance
    without the sandbox doesn't penalise anyone."""
    current = _content_hash(rule.to_string)
    if batch_context is not None:
        res = batch_context["samples"].get(rule.id, {}).get(current)
    else:
        from app.core.db_class.rule_tester import RuleSampleResult
        row = (RuleSampleResult.query.filter_by(rule_id=rule.id, content_hash=current)
               .order_by(RuleSampleResult.created_at.desc()).first())
        res = (row.content_hash, row.total, row.detected, row.false_positives, row.errors) if row else None
    if not res or res[0] != current or not res[1]:
        return None
    _, total, detected, fps, errors = res
    checks = {
        "tested_on_samples": True,
        "detects_its_samples": (detected or 0) > 0,
        "no_false_positives": (fps or 0) == 0,
        "no_test_errors": (errors or 0) == 0,
    }
    weights = {"tested_on_samples": 5, "detects_its_samples": 10, "no_false_positives": 10, "no_test_errors": 5}
    earned, total_w = _weighted(checks, weights)
    return earned, total_w, checks


def _score_external_checks(rule, batch_context=None):
    """YARA only, when the admin enabled them (editor.external_checks): YARA-X compiles it, it
    follows the CCCS YARA standard, yaraQA finds no issue. A tool that can't judge the rule alone
    (it uses another Rulezet rule, the tool is missing) is left out. None = not applicable."""
    if (rule.format or "").lower() != "yara" or not rule.to_string:
        return None
    try:
        from app.features.editor.external_checks import run_checks
        results = run_checks(rule.to_string)
    except Exception:
        return None
    checks, weights = {}, {}
    for tool, key, weight in (("yarax", "compiles_with_yara_x", 5), ("cccs", "follows_cccs_standard", 5),
                              ("yaraqa", "clean_for_yaraqa", 5)):
        r = results.get(tool)
        if not r or not r.get("available"):
            continue
        messages = " ".join(str(e.get("message", "")) for e in r.get("errors") or []).lower()
        if tool == "yarax" and ("unknown identifier" in messages or "unknown module" in messages):
            continue                      # depends on other rules / a module: Rulezet's own check covers it
        ok = bool(r.get("ok")) and (tool != "yaraqa" or not r.get("warnings"))
        checks[key], weights[key] = ok, weight
    if not checks:
        return None
    earned, total = _weighted(checks, weights)
    return earned, total, checks


def compute_engagement_boost(rule, batch_context=None) -> float:
    """Popularity signal, log-scaled and capped — a bonus on top of the base
    score, never a substitute for it (see module docstring)."""
    if batch_context is not None:
        favorites = batch_context["favorites"].get(rule.id, 0)
        comments = batch_context["comments"].get(rule.id, 0)
    else:
        favorites = rule.favorited_by_users_assocs.count()
        comments = rule.comments_rule.count()
    net_votes = max((rule.vote_up or 0) - (rule.vote_down or 0), 0)
    raw = math.log1p(favorites) * 3 + math.log1p(net_votes) * 2 + math.log1p(comments) * 1.5
    return round(min(raw, 10.0), 2)


def compute_quality_score(rule, batch_context=None) -> Tuple[float, Dict[str, Any]]:
    """Returns (base_score 0-100, breakdown dict). base_score is the objective
    documentation/traceability/validity signal — engagement is reported
    separately inside breakdown, never folded into base_score itself.

    batch_context (see build_batch_context()) replaces this rule's per-row
    tag/ATT&CK/history/favorite/comment queries with dict lookups — pass it
    when scoring many rules in one job run; leave it None for a single rule
    (the interactive write-time hooks), where a handful of queries is fine."""
    rule_type = _get_rule_type_instance(rule.format)

    trace_earned, trace_total, trace_checks = _score_traceability(rule)
    doc_earned, doc_total, doc_checks = _score_documentation(rule)
    meta_earned, meta_total, meta_checks = _score_metadata(rule, rule_type, batch_context)
    valid_earned, valid_total, valid_checks = _score_validity(rule, rule_type, batch_context)
    review_earned, review_total, review_checks = _score_review(rule, batch_context)
    usage_earned, usage_total, usage_checks = _score_usage(rule, batch_context)
    categories = {
        "traceability":  {"earned": trace_earned,  "total": trace_total,  "checks": trace_checks},
        "authorship":    {"earned": doc_earned,    "total": doc_total,    "checks": doc_checks},
        "metadata":      {"earned": meta_earned,   "total": meta_total,   "checks": meta_checks},
        "validity":      {"earned": valid_earned,  "total": valid_total,  "checks": valid_checks},
        "review":        {"earned": review_earned, "total": review_total, "checks": review_checks},
        "usage":         {"earned": usage_earned,  "total": usage_total,  "checks": usage_checks},
    }
    # Counted only when they apply (tested on samples / YARA with external checks on)
    for key, scored in (("field_reports", _score_field_reports(rule, batch_context)),
                        ("testing", _score_testing(rule, batch_context)),
                        ("external_checks", _score_external_checks(rule, batch_context))):
        if scored is None:
            categories[key] = {"earned": 0, "total": 0, "checks": {}, "not_applicable": True}
        else:
            categories[key] = {"earned": scored[0], "total": scored[1], "checks": scored[2]}

    total_earned = sum(c["earned"] for c in categories.values())
    total_possible = sum(c["total"] for c in categories.values())
    base_score = round((total_earned / total_possible) * 100, 2) if total_possible else 0.0

    engagement_boost = compute_engagement_boost(rule, batch_context)

    breakdown = {
        "base_score": base_score,
        "engagement_boost": engagement_boost,
        "display_score": round(min(100.0, base_score + engagement_boost), 2),
        "categories": categories,
    }
    return base_score, breakdown


def quality_fingerprint(rule) -> str:
    """A cheap signature of everything the score reads (one small query per source): content and
    edit time, tags, ATT&CK, bundles, scopes, reviews, sample tests, AI analyses, similarity
    results, source updates, favorites, comments. Same fingerprint = same score: no need to
    recompute. Stored in the breakdown by recompute_rule_quality_score()."""
    from sqlalchemy import func
    from app.core.db_class.ai import AIGeneration
    from app.core.db_class.bundle import BundleRuleAssociation
    from app.core.db_class.comment import Comment
    from app.core.db_class.rule import RuleFavoriteUser, RuleReview, RuleScope
    from app.core.db_class.rule_tester import RuleSampleResult
    from app.core.db_class.similarity import RuleSimilarity

    def sig(model, *cols, **flt):
        q = db.session.query(func.count(), *[func.max(c) for c in cols]).select_from(model)
        for k, v in flt.items():
            q = q.filter(getattr(model, k) == v)
        return '/'.join(str(x) for x in q.one())

    parts = [
        _content_hash(rule.to_string)[:16], str(rule.last_modif), rule.license or '', rule.description and len(rule.description),
        rule.author or '', rule.source or '', rule.cve_id or '', getattr(rule, 'written_with', None) or '',
        rule.vote_up, rule.vote_down,
        sig(RuleTagAssociation, RuleTagAssociation.id, rule_id=rule.id),
        sig(RuleAttackAssociation, RuleAttackAssociation.id, rule_id=rule.id),
        sig(BundleRuleAssociation, BundleRuleAssociation.id, rule_id=rule.id),
        sig(RuleScope, RuleScope.updated_at, rule_id=rule.id),
        sig(RuleReview, RuleReview.created_at, rule_id=rule.id),
        sig(RuleSampleResult, RuleSampleResult.id, rule_id=rule.id),
        sig(AIGeneration, AIGeneration.id, rule_id=rule.id),
        sig(RuleSimilarity, RuleSimilarity.id, rule_id=rule.id),
        sig(RuleUpdateHistory, RuleUpdateHistory.id, rule_id=rule.id),
        sig(RuleFavoriteUser, RuleFavoriteUser.id, rule_id=rule.id),
        sig(Comment, Comment.id, rule_id=rule.id),
    ]
    import hashlib
    return hashlib.sha1('|'.join(str(p) for p in parts).encode()).hexdigest()


def ensure_fresh_quality(rule) -> bool:
    """Called when someone opens the rule: recompute only if never scored or if something the
    score reads changed since (fingerprint differs). Returns True when it recomputed.
    Never raises — a scoring problem must not break the rule page."""
    try:
        breakdown = rule.quality_score_breakdown or {}
        if rule.quality_score is not None and breakdown.get("fingerprint") == quality_fingerprint(rule):
            return False
        recompute_rule_quality_score(rule)
        return True
    except Exception:
        db.session.rollback()
        return False


def recompute_rule_quality_score(rule, commit: bool = True, batch_context=None) -> float:
    """Call after any write that can change a rule's score (content edit,
    tag/ATT&CK/favorite/vote change, GitHub update acceptance, or in bulk from
    the 'compute_rule_quality_score' job). Isolated commit — never interferes
    with the caller's own transaction, same pattern as the github_path
    backfill in update_class.py."""
    score, breakdown = compute_quality_score(rule, batch_context=batch_context)
    try:
        breakdown["fingerprint"] = quality_fingerprint(rule)
    except Exception:
        breakdown["fingerprint"] = None
    rule.quality_score = score
    rule.quality_score_breakdown = breakdown
    rule.quality_score_computed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    if commit:
        db.session.commit()
    return score


def build_batch_context(rule_ids) -> Dict[str, Dict[int, Any]]:
    """One query per signal for a whole batch of rule ids, instead of the
    ~5 queries per rule that compute_quality_score()/compute_engagement_boost()
    fall back to without a batch_context — that's what made the
    'compute_rule_quality_score' job slow (thousands of rules x 5 round trips
    each). Absence of a rule_id from a dict IS the correct "no tags / no
    ATT&CK / no history / no favorites / no comments" answer, not a
    not-yet-computed marker, so callers can use plain `in`/`.get(id, 0)`."""
    rule_ids = list(rule_ids)
    if not rule_ids:
        return {"meaningful_tags": {}, "has_attack": {}, "last_history_failed": {}, "favorites": {}, "comments": {},
                "reviews": {}, "samples": {}, "duplicates": {}, "in_bundle": {}, "ai_analysis": {}, "scopes": {}}

    from sqlalchemy import func
    from app.core.db_class.comment import Comment
    from app.core.db_class.rule import RuleFavoriteUser

    tag_rows = (
        db.session.query(RuleTagAssociation.rule_id, Tag.name)
        .join(Tag, RuleTagAssociation.tag_id == Tag.id)
        .filter(RuleTagAssociation.rule_id.in_(rule_ids))
        .all()
    )
    meaningful_tags = {}
    for rule_id, name in tag_rows:
        if not str(name).lower().startswith(_DEFAULT_TAG_PREFIXES):
            meaningful_tags[rule_id] = True

    attack_rows = (
        db.session.query(RuleAttackAssociation.rule_id)
        .filter(RuleAttackAssociation.rule_id.in_(rule_ids))
        .distinct()
        .all()
    )
    has_attack = {rid: True for (rid,) in attack_rows}

    # Ordered by (rule_id, analyzed_at desc): within each rule_id's run of
    # rows, the first one seen is its most recent — same result as the
    # per-rule "order by analyzed_at desc, take first" query, in one pass.
    history_rows = (
        db.session.query(RuleUpdateHistory.rule_id, RuleUpdateHistory.success)
        .filter(RuleUpdateHistory.rule_id.in_(rule_ids))
        .order_by(RuleUpdateHistory.rule_id, RuleUpdateHistory.analyzed_at.desc())
        .all()
    )
    last_history_failed = {}
    for rule_id, success in history_rows:
        if rule_id not in last_history_failed:
            last_history_failed[rule_id] = (success is False)
    last_history_failed = {rid: v for rid, v in last_history_failed.items() if v}

    favorites = dict(
        db.session.query(RuleFavoriteUser.rule_id, func.count(RuleFavoriteUser.id))
        .filter(RuleFavoriteUser.rule_id.in_(rule_ids))
        .group_by(RuleFavoriteUser.rule_id)
        .all()
    )

    comments = dict(
        db.session.query(Comment.rule_id, func.count(Comment.id))
        .filter(Comment.rule_id.in_(rule_ids))
        .group_by(Comment.rule_id)
        .all()
    )

    from app.core.db_class.rule import RuleReview
    from app.core.db_class.rule_tester import RuleSampleResult
    reviews = {}
    for rid, uid, verdict, chash in (db.session.query(RuleReview.rule_id, RuleReview.user_id, RuleReview.verdict,
                                                      RuleReview.content_hash)
                                     .filter(RuleReview.rule_id.in_(rule_ids)).all()):
        reviews.setdefault(rid, []).append((uid, verdict, chash))
    samples = {}
    for rid, chash, total, detected, fps, errors in (
            db.session.query(RuleSampleResult.rule_id, RuleSampleResult.content_hash, RuleSampleResult.total,
                             RuleSampleResult.detected, RuleSampleResult.false_positives, RuleSampleResult.errors)
            .filter(RuleSampleResult.rule_id.in_(rule_ids))
            .order_by(RuleSampleResult.rule_id, RuleSampleResult.created_at.desc()).all()):
        samples.setdefault(rid, {}).setdefault(chash, (chash, total, detected, fps, errors))   # newest per version

    from app.core.db_class.bundle import BundleRuleAssociation
    from app.core.db_class.rule import Rule
    from app.core.db_class.similarity import RuleSimilarity
    from sqlalchemy.orm import aliased
    me, other = aliased(Rule), aliased(Rule)
    duplicates = {rid: True for (rid,) in (
        db.session.query(RuleSimilarity.rule_id)
        .join(me, me.id == RuleSimilarity.rule_id).join(other, other.id == RuleSimilarity.similar_rule_id)
        .filter(RuleSimilarity.rule_id.in_(rule_ids), RuleSimilarity.score >= DUPLICATE_SIMILARITY,
                other.is_deleted == False, other.creation_date < me.creation_date)   # noqa: E712
        .distinct().all())}
    in_bundle = {rid: True for (rid,) in db.session.query(BundleRuleAssociation.rule_id)
                 .filter(BundleRuleAssociation.rule_id.in_(rule_ids)).distinct().all()}

    from app.core.db_class.ai import AIGeneration
    ai_analysis = {rid: True for (rid,) in db.session.query(AIGeneration.rule_id)
                   .filter(AIGeneration.rule_id.in_(rule_ids), AIGeneration.agent_key == 'rule_analysis',
                           AIGeneration.is_public == True).distinct().all()}   # noqa: E712

    from app.core.db_class.rule import RuleScope
    scopes = {}
    for rid, works in db.session.query(RuleScope.rule_id, RuleScope.works).filter(RuleScope.rule_id.in_(rule_ids)).all():
        w, b = scopes.get(rid, (0, 0))
        scopes[rid] = (w + 1, b) if works else (w, b + 1)

    return {
        "scopes": scopes,
        "ai_analysis": ai_analysis,
        "duplicates": duplicates,
        "in_bundle": in_bundle,
        "reviews": reviews,
        "samples": samples,
        "meaningful_tags": meaningful_tags,
        "has_attack": has_attack,
        "last_history_failed": last_history_failed,
        "favorites": favorites,
        "comments": comments,
    }


def refresh_engagement_boost(rule, commit: bool = True) -> None:
    """Cheap counterpart to recompute_rule_quality_score() for high-frequency,
    engagement-only writes (vote up/down) that can never move the base score
    (votes aren't a scoring criterion, only a boost — see module docstring).
    Updates just the boost/display_score inside the existing breakdown
    without re-running validate()/documentation checks on every click.
    Falls back to a full recompute if the rule has never been analyzed yet
    (no breakdown to patch)."""
    if not rule.quality_score_breakdown or rule.quality_score is None:
        recompute_rule_quality_score(rule, commit=commit)
        return

    breakdown = dict(rule.quality_score_breakdown)
    breakdown["engagement_boost"] = compute_engagement_boost(rule)
    breakdown["display_score"] = round(min(100.0, rule.quality_score + breakdown["engagement_boost"]), 2)
    try:
        breakdown["fingerprint"] = quality_fingerprint(rule)
    except Exception:
        pass
    rule.quality_score_breakdown = breakdown
    rule.quality_score_computed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    if commit:
        db.session.commit()
