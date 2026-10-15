"""SQLAlchemy models, one module per feature:

    user, role, rule, rule_proposal, rule_relation, rule_tester, comment, report,
    tag, bundle, git, attack, similarity, alert, notification, workspace, blog,
    connector, misp, velociraptor, ai, pivotick, gamification, job,
    task_scheduler, activity_log, setting — plus common (shared column types/helpers).

Import a model from its module: `from app.core.db_class.rule import Rule`.
Every module is loaded here so SQLAlchemy knows all models (relationships
are declared by class name) and their event listeners are registered.
"""
from app.core.db_class import (  # noqa: F401
    common, user, role, rule, rule_proposal, rule_relation, rule_tester, comment, report,
    tag, bundle, git, attack, similarity, alert, notification, workspace, blog,
    connector, misp, velociraptor, ai, pivotick, gamification, job, task_scheduler, activity_log,
    setting,
)
