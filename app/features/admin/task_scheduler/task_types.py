"""
task_types.py — registry of schedulable task types for the Admin Task
Scheduler (see docs/design/admin_task_scheduler.md). Adding a task type is
a matter of adding an entry here — never touch the generic engine
(scheduler_engine.py) or the admin UI's list/table. The job_type must
already exist as a @register_handler in job_handlers.py; this registry only
describes how the scheduling form should build its target_payload.

Phase 1 subset: only task types whose job handler already exists AND whose
payload shape is simple enough for a generic picker (§9 of the design doc
lists what's excluded and why — e.g. Similarity/Git Import need a new
handler first, Field Parser/Bulk Platform Tagging need a richer config
picker than any target_picker below covers yet). Extending this dict is the
whole point of the registry — see it as a starting set, not a ceiling.

target_picker values understood by task_scheduler.html:
    'rule_list_select'   — <rule-list mode="select"> picks target_payload.filters/rule_ids
    'format_filter_only' — a plain <select> of rule formats, payload {format}
                           (or {<format_key>} when the handler names it differently)
    'connector_select'   — a plain <select> of Connector rows, payload {connector_id}
    'none'               — nothing to target, payload {}

extra_options[].type values understood by task_scheduler.html:
    'bool' | 'text'
    'multiselect'  — checkboxes over opt['options'] ([{value, label}]), value is a list
    'saved_config' — a <select> of the saved Bulk Parse Fields configs of
                     opt['config_type'] ('field_parser' | 'platform_tags');
                     opt['allow_all'] adds the "every saved config" choice
Every option is merged into target_payload, whatever the target_picker.

'required_options' lists the extra_options keys that must be non-empty —
checked by task_scheduler_core on save and on an ad-hoc run.
"""
from app.features.tags.imported_tags_core import FORMAT_TAG_SOURCES

_NATIVE_TAG_FORMAT_OPTIONS = [{'value': f, 'label': f'{f} — {where}'} for f, where in FORMAT_TAG_SOURCES.items()]

TASK_TYPES = {
    'quality_score': {
        'label': 'Rule Quality Score — (re)analyze',
        'icon': 'fa-solid fa-gauge-high',
        'job_type': 'compute_rule_quality_score',
        'target_picker': 'rule_list_select',
    },
    'attack_parser': {
        'label': 'ATT&CK Auto-parse',
        'icon': 'fa-solid fa-crosshairs',
        'job_type': 'bulk_parse_attack_rules',
        'target_picker': 'format_filter_only',
    },
    'misp_update_data': {
        'label': 'MISP — Update taxonomies & galaxies (imported only)',
        'icon': 'fa-solid fa-rotate',
        'job_type': 'update_misp_data',
        'target_picker': 'none',
    },
    'misp_import_all_taxonomies': {
        'label': 'MISP — Import all new taxonomies',
        'icon': 'fa-solid fa-tags',
        'job_type': 'import_all_taxonomies',
        'target_picker': 'none',
    },
    'misp_import_all_galaxies': {
        'label': 'MISP — Import all new galaxies',
        'icon': 'fa-solid fa-tags',
        'job_type': 'import_all_galaxies',
        'target_picker': 'none',
    },
    'attack_update_data': {
        'label': 'ATT&CK — Update MITRE data',
        'icon': 'fa-brands fa-github',
        'job_type': 'update_attack_data',
        'target_picker': 'none',
    },
    'db_backup': {
        'label': 'Database Backup',
        'icon': 'fa-solid fa-database',
        'job_type': 'db_backup',
        'target_picker': 'none',
    },
    'rule_validation_run': {
        'label': 'Rule Validation (false-positive gate)',
        'icon': 'fa-solid fa-shield-check',
        'job_type': 'rule_validation_run',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'full', 'type': 'bool', 'label': 'Full scan (ignore last-sync date)', 'default': False},
        ],
    },
    'activity_log_purge': {
        'label': 'Activity Log — Purge old entries',
        'icon': 'fa-solid fa-broom',
        'job_type': 'delete_activity_logs',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'action_filter', 'type': 'text', 'label': 'Only actions starting with (optional)', 'default': ''},
        ],
        # A scheduled purge always targets every matching entry — there is no
        # per-run manual log_ids selection like the ad-hoc admin action has.
        'fixed_payload': {'delete_all': True},
    },
    'connector_pull': {
        'label': 'Connector — Pull one federation source',
        'icon': 'fa-solid fa-plug',
        'job_type': 'connector_pull',
        'target_picker': 'connector_select',
    },
    'github_repo_resync': {
        'label': 'Git Sources — resync registry',
        'icon': 'fa-brands fa-git-alt',
        'job_type': 'github_repo_resync',
        'target_picker': 'none',
        # Same full recompute as the Git Sources page's admin "Resync"
        # button — a correctness backstop for GithubRepo's incremental sync
        # (see github_repo_core.py), safe to run repeatedly/on a schedule.
    },
    'relink_rules': {
        'label': 'Linked rules — look again for links between rules (Wazuh, Kunai, YARA)',
        'icon': 'fa-solid fa-diagram-project',
        'job_type': 'relink_rules',
        'target_picker': 'none',
        # The detection an import runs, over rules already in the database:
        # Wazuh children imported before their parent, Kunai rules sharing a
        # hash across imports, YARA rules imported before a rule they name.
        # Only adds links, never duplicates — safe after every Git import.
        'extra_options': [
            {'key': 'formats', 'type': 'multiselect', 'label': 'Rule formats',
             'options': [{'value': 'wazuh', 'label': 'Wazuh — if_sid / if_matched_sid parents'},
                         {'value': 'kunai', 'label': 'Kunai — rules sharing a hash'},
                         {'value': 'yara', 'label': 'YARA — rules a condition names (long: compiles every rule, ~30 min for 250k)'}],
             'default': ['wazuh', 'kunai']},
            {'key': 'source', 'type': 'text', 'label': 'Only rules from this repository URL (optional)', 'default': ''},
        ],
        'required_options': ['formats'],
    },
    'rule_git_mirror_sync': {
        'label': 'Rulesets — sync',
        'icon': 'fa-brands fa-git-alt',
        'job_type': 'rule_git_mirror_sync',
        'target_picker': 'none',
        # RuleMirrorConfig.enabled gates this — scheduling/running the task
        # with the feature turned off just fails fast with a clear message
        # (see rule_mirror_core.sync_mirror), it never syncs unexpectedly.
    },
    'native_tags_import': {
        'label': 'Tags — re-parse the native tags of every rule',
        'icon': 'fa-solid fa-tags',
        'job_type': 'import_native_tags',
        'target_picker': 'none',
        # Same job as Bulk Parse Fields → Imported Tags: idempotent, it also
        # detaches Imported tags a rule's content no longer yields — safe to
        # run on a schedule (e.g. after a Git import task).
        'extra_options': [
            {'key': 'formats', 'type': 'multiselect', 'label': 'Rule formats to re-parse',
             'options': _NATIVE_TAG_FORMAT_OPTIONS, 'default': list(FORMAT_TAG_SOURCES)},
        ],
        'required_options': ['formats'],
    },
    'platform_tagging': {
        'label': 'Tags — detect & tag platforms (saved config)',
        'icon': 'fa-solid fa-desktop',
        'job_type': 'bulk_tag_platforms',
        'target_picker': 'format_filter_only',
        'format_key': 'format_filter',
        # The config is read live at each run, so editing it on the Bulk
        # Parse Fields page changes what the next scheduled run does.
        'extra_options': [
            {'key': 'config_id', 'type': 'saved_config', 'config_type': 'platform_tags', 'allow_all': True,
             'label': 'Platform-tag config', 'default': 'ALL'},
        ],
        'required_options': ['config_id'],
    },
    'field_parser': {
        'label': 'Field Parser — re-parse rule fields (saved config)',
        'icon': 'fa-solid fa-wand-magic-sparkles',
        'job_type': 'bulk_parse_fields',
        'target_picker': 'format_filter_only',
        'format_key': 'format_filter',
        'extra_options': [
            {'key': 'config_id', 'type': 'saved_config', 'config_type': 'field_parser',
             'label': 'Field Parser config (license, author, version…)', 'default': ''},
            {'key': 'rescan_cve', 'type': 'bool', 'label': 'Also re-scan CVE / vulnerability ids', 'default': False},
        ],
        'required_options': ['config_id'],
    },
    'github_import': {
        'label': 'Git — import rules from a repository (GitHub, GitLab, Gitea…)',
        'icon': 'fa-brands fa-git-alt',
        'job_type': 'github_import',
        'target_picker': 'none',
        # Same import as the Git Import page (results land in its import
        # history). Re-running it only adds the rules that are new since
        # last time — existing ones are skipped as duplicates.
        'extra_options': [
            {'key': 'url', 'type': 'text', 'label': 'Repository URL on any git host (https://gitlab.com/group/repo, https://github.com/owner/repo…)', 'default': ''},
            {'key': 'branch', 'type': 'text', 'label': 'Branch — blank uses the default branch', 'default': ''},
            {'key': 'license', 'type': 'text', 'label': 'License to apply when a rule has none (e.g. MIT)', 'default': ''},
        ],
        'required_options': ['url'],
    },
    'github_branch_backfill': {
        'label': 'Git Sources — backfill missing rule branches',
        'icon': 'fa-solid fa-code-branch',
        'job_type': 'github_repo_branch_backfill',
        'target_picker': 'none',
    },
    'suricata_audit': {
        'label': 'Suricata — audit rules (report only)',
        'icon': 'fa-solid fa-magnifying-glass-chart',
        'job_type': 'audit_suricata_rules',
        'target_picker': 'none',
        # Read-only: counts valid / Sagan-looking / broken rules in the job
        # log, changes nothing.
    },
    'suricata_deep_validate': {
        'label': 'Suricata — deep validation with the real engine',
        'icon': 'fa-solid fa-shield-virus',
        'job_type': 'deep_validate_suricata_rules',
        'target_picker': 'none',
        # Fails fast when SURICATA_BINARY_PATH is not configured.
        'extra_options': [
            {'key': 'limit', 'type': 'text', 'label': 'Rules per run (max 5000)', 'default': '500'},
        ],
    },
    'gamification_recompute': {
        'label': 'Gamification — recompute all users',
        'icon': 'fa-solid fa-star',
        'job_type': 'recompute_gamification',
        'target_picker': 'none',
    },
    'ai_rule_analysis': {
        'label': 'AI Rule Analysis — generate reports',
        'icon': 'fa-solid fa-robot',
        'job_type': 'ai_generate',
        'target_picker': 'rule_list_select',
        # This job runs in job_worker.py's background lane (see AI_00
        # FOUNDATION.md §8) and is deliberately bounded per invocation
        # (batch_size/max_seconds below) — scheduling it to recur (e.g.
        # nightly) is the intended way to run it, not a one-shot "ALL" pick.
        'fixed_payload': {'agent_key': 'rule_analysis'},
        'extra_options': [
            {'key': 'model', 'type': 'text', 'label': 'Ollama model (e.g. qwen2.5:7b) — blank uses the agent default', 'default': ''},
            {'key': 'batch_size', 'type': 'text', 'label': 'Rules per run', 'default': '50'},
            {'key': 'max_seconds', 'type': 'text', 'label': 'Max seconds per run', 'default': '900'},
            {'key': 'regenerate_existing', 'type': 'bool', 'label': 'Regenerate rules that already have an analysis', 'default': False},
            {'key': 'default_public', 'type': 'bool', 'label': 'Publish new reports immediately', 'default': True},
        ],
    },
}


def serialize_task_types():
    """JSON-safe view of the registry for GET /admin/tasks/types — drops
    nothing sensitive (there isn't any), just here so the route doesn't
    reach into TASK_TYPES' internals directly."""
    return {
        key: {
            'label': t['label'],
            'icon': t['icon'],
            'target_picker': t['target_picker'],
            'format_key': t.get('format_key', 'format'),
            'extra_options': t.get('extra_options', []),
            'required_options': t.get('required_options', []),
        }
        for key, t in TASK_TYPES.items()
    }
