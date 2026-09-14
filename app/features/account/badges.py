"""
badges.py — the badge catalog for the gamification system.

Single source of truth for every badge's definition (name, description,
icon, unlock rule). Previously this list was duplicated ad hoc in
app/static/js/account/UserContributionStatsComponent.js and recomputed
fresh from raw numbers on every page render, with no way to know a badge
was *just* unlocked. Unlock *events* are now persisted (see
UserBadge in app/core/db_class/db.py) — this module only defines what a
badge is and how to check it; app/features/account/account_core.py's
evaluate_badges() is what actually grants them.

Adding a new badge is just adding an entry here — no migration needed,
since the catalog itself isn't a DB table.

'color' picks from the same accent palette already used by KPI/chart
cards elsewhere (see CLAUDE.md: .ud-kpi-card--blue/teal/green/gold/
purple/orange) so a new badge tile matches the rest of the page instead
of introducing a new palette.
"""

BADGES = [
    {
        'key': 'bronze_contributor',
        'name': 'Bronze Contributor',
        'description': 'Reach 1,000 total points.',
        'icon': 'fas fa-star',
        'color': 'orange',
        'rulezy_pose': 'simple',
        'check': lambda g: (g.total_points or 0) >= 1000,
    },
    {
        'key': 'silver_contributor',
        'name': 'Silver Contributor',
        'description': 'Reach 10,000 total points.',
        'icon': 'fas fa-star',
        'color': 'teal',
        'rulezy_pose': 'armcross',
        'check': lambda g: (g.total_points or 0) >= 10000,
    },
    {
        'key': 'gold_contributor',
        'name': 'Gold Contributor',
        'description': 'Reach 50,000 total points.',
        'icon': 'fas fa-star',
        'color': 'gold',
        'rulezy_pose': 'armcross',
        'check': lambda g: (g.total_points or 0) >= 50000,
    },
    {
        'key': 'curator_rookie',
        'name': 'Curator Rookie',
        'description': 'Get 5 edit suggestions accepted.',
        'icon': 'fas fa-glasses',
        'color': 'blue',
        'rulezy_pose': 'lookup',
        'check': lambda g: (g.suggestions_accepted or 0) >= 5,
    },
    {
        'key': 'quality_master',
        'name': 'Quality Master',
        'description': 'Get 25 edit suggestions accepted.',
        'icon': 'fas fa-cogs',
        'color': 'green',
        'rulezy_pose': 'rule-fixer',
        'check': lambda g: (g.suggestions_accepted or 0) >= 25,
    },
    {
        'key': 'veteran_contributor',
        'name': 'Veteran Contributor',
        'description': 'Reach level 5.',
        'icon': 'fas fa-brain',
        'color': 'purple',
        'rulezy_pose': 'reflexion',
        'check': lambda g: (g.current_level or 1) >= 5,
    },
    {
        'key': 'bundle_architect',
        'name': 'Bundle Architect',
        'description': 'Publish 5 bundles.',
        'icon': 'fas fa-layer-group',
        'color': 'teal',
        'rulezy_pose': 'db',
        'check': lambda g: (g.bundles_owned or 0) >= 5,
    },
    {
        'key': 'range_tester',
        'name': 'Range Tester',
        'description': 'Run rule tests on 10 different days.',
        'icon': 'fas fa-flask',
        'color': 'orange',
        'rulezy_pose': 'rule-fixer',
        'check': lambda g: (g.rule_tests_contributed or 0) >= 10,
    },
    {
        'key': 'mitre_mapper',
        'name': 'MITRE Mapper',
        'description': 'Manually map 20 ATT&CK techniques.',
        'icon': 'fas fa-crosshairs',
        'color': 'blue',
        'rulezy_pose': 'analyseRule',
        'check': lambda g: (g.attack_mappings_contributed or 0) >= 20,
    },
    {
        'key': 'consistency_streak',
        'name': 'Consistency Streak',
        'description': 'Contribute something 7 days in a row.',
        'icon': 'fas fa-fire-alt',
        'color': 'orange',
        'rulezy_pose': 'repos',
        'check': lambda g: (g.consecutive_days_active or 0) >= 7,
    },
    {
        'key': 'all_rounder',
        'name': 'All-Rounder',
        'description': 'Own a rule, publish a bundle, run a test and map an ATT&CK technique — at least once each.',
        'icon': 'fas fa-chess-king',
        'color': 'purple',
        'rulezy_pose': 'chatbot',
        'check': lambda g: (
            (g.rules_owned or 0) > 0 and (g.bundles_owned or 0) > 0 and
            (g.rule_tests_contributed or 0) > 0 and (g.attack_mappings_contributed or 0) > 0
        ),
    },
]

BADGES_BY_KEY = {b['key']: b for b in BADGES}


def badges_catalog_json() -> list:
    """Badge catalog without the check() lambdas — safe to serialize for
    the API / the "How to earn points" page."""
    return [
        {'key': b['key'], 'name': b['name'], 'description': b['description'],
         'icon': b['icon'], 'color': b['color'], 'rulezy_pose': b['rulezy_pose']}
        for b in BADGES
    ]
