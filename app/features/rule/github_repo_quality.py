"""
github_repo_quality.py — how good a Git repository is as a source of rules, 0-100.

  rules_quality   50  average quality score of its rules (quality_score_core.py)
  import_health   15  share of its files that imported (not left as bad rules)
  valid_rules     10  share of its rules passing Rulezet's syntax check
  licensed        10  share of its rules with a license
  kept_up_to_date 10  synced in the last 30 days (5 if in the last 90)
  no_conflicts     5  no rule in conflict with another source
plus, shown next to it (not scored): reviewed / approved rules, rules tested on samples.

Stored on GithubRepo (quality_score, quality_breakdown, quality_computed_at); computed by the
'repo_quality' workflow task (job handler compute_repo_quality) — never on page load.
"""
import datetime

from sqlalchemy import func

from app import db
from app.core.db_class.git import GithubRepo
from app.core.db_class.rule import InvalidRuleModel, Rule, RuleReview
from app.features.rule.rule_core import _active

WEIGHTS = {'rules_quality': 50, 'import_health': 15, 'valid_rules': 10, 'licensed': 10,
           'kept_up_to_date': 10, 'no_conflicts': 5}


def compute(repo: GithubRepo) -> dict:
    rows = (_active().filter(Rule.source == repo.url)
            .with_entities(Rule.id, Rule.quality_score, Rule.quality_score_breakdown, Rule.license).all())
    n = len(rows)
    scored = [r[1] for r in rows if r[1] is not None]
    valid = [((r[2] or {}).get('categories') or {}).get('validity', {}).get('checks', {}).get('passes_validation')
             for r in rows if r[2]]
    licensed = sum(1 for r in rows if r[3] and str(r[3]).strip().lower() not in ('', 'unknown', 'none', 'n/a'))
    bad = InvalidRuleModel.query.filter_by(url=repo.url).count()
    ids = [r[0] for r in rows]
    approved = (db.session.query(func.count(func.distinct(RuleReview.rule_id)))
                .filter(RuleReview.rule_id.in_(ids), RuleReview.verdict == 'approved').scalar() or 0) if ids else 0
    try:
        from app.core.db_class.rule_tester import RuleSampleResult
        tested = (db.session.query(func.count(func.distinct(RuleSampleResult.rule_id)))
                  .filter(RuleSampleResult.rule_id.in_(ids)).scalar() or 0) if ids else 0
    except Exception:
        tested = 0

    now = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)
    synced = repo.last_synced_at.replace(tzinfo=None) if repo.last_synced_at else None
    age_days = (now - synced).days if synced else None

    parts = {
        'rules_quality': (sum(scored) / len(scored) / 100) if scored else 0.0,
        'import_health': (n / (n + bad)) if (n + bad) else 0.0,
        'valid_rules': (sum(1 for v in valid if v) / len(valid)) if valid else 0.0,
        'licensed': (licensed / n) if n else 0.0,
        'kept_up_to_date': 1.0 if age_days is not None and age_days <= 30 else 0.5 if age_days is not None and age_days <= 90 else 0.0,
        'no_conflicts': 1.0 if not repo.conflict_count else 0.0,
    }
    points = {k: round(WEIGHTS[k] * v, 1) for k, v in parts.items()}
    score = round(sum(points.values()), 1) if n else 0.0
    return {
        'score': score,
        'points': points, 'weights': WEIGHTS,
        'facts': {
            'rules': n, 'rules_scored': len(scored),
            'average_rule_score': round(sum(scored) / len(scored), 1) if scored else None,
            'bad_rules': bad, 'valid_rules': sum(1 for v in valid if v), 'licensed_rules': licensed,
            'last_synced_days': age_days, 'conflicts': repo.conflict_count or 0,
            'approved_rules': approved, 'tested_rules': tested,
        },
    }


def recompute(repo: GithubRepo, commit: bool = True) -> float:
    result = compute(repo)
    repo.quality_score = result['score'] if result['facts']['rules'] else None
    repo.quality_breakdown = result
    repo.quality_computed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    if commit:
        db.session.commit()
    return repo.quality_score
