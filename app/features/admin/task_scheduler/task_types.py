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
    'select'       — a <select> over opt['options'] ([{value, label}]), or over choices read from the
                     database at serialization when opt['options_from'] names them (see _with_options)
    'saved_config' — a <select> of the saved Bulk Parse Fields configs of
                     opt['config_type'] ('field_parser' | 'platform_tags');
                     opt['allow_all'] adds the "every saved config" choice
Every option is merged into target_payload, whatever the target_picker.

'required_options' lists the extra_options keys that must be non-empty —
checked by task_scheduler_core on save and on an ad-hoc run.
"""
from app.features.tags.imported_tags_core import FORMAT_TAG_SOURCES
from app.features.admin.task_scheduler.actions import FIGURES as _FIGURES, OPERATORS as _OPERATORS

_NATIVE_TAG_FORMAT_OPTIONS = [{'value': f, 'label': f'{f} — {where}'} for f, where in FORMAT_TAG_SOURCES.items()]

TASK_TYPES = {
    'quality_score': {
        'label': 'Rule Quality Score — (re)analyze',
        'icon': 'fa-solid fa-gauge-high',
        'job_type': 'compute_rule_quality_score',
        'target_picker': 'rule_list_select',
    },
    'repo_quality': {
        'label': 'Git Sources — quality score',
        'icon': 'fa-solid fa-ranking-star',
        'job_type': 'compute_repo_quality',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'scope', 'type': 'select', 'label': 'Repositories', 'default': 'all',
             'options': [{'value': 'all', 'label': 'Every Git source'}, {'value': 'circl', 'label': 'CIRCL repositories only'}]},
        ],
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
    'db_backup_rotate': {
        'label': 'Database backup + rotation (keep the last N)',
        'icon': 'fa-solid fa-box-archive',
        'job_type': 'db_backup_rotate',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'keep', 'type': 'text', 'label': 'Backups to keep (3 minimum)', 'default': '10'},
        ],
        'required_options': ['keep'],
    },
    'rule_validation_run': {
        'label': 'Rule Validation (false-positive gate)',
        'icon': 'fa-solid fa-vial-circle-check',   # fa-shield-check is Font Awesome Pro, not in the bundled free set
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
    'bad_rules_retry': {
        'label': 'Bad rules — try them again and link the rules they name',
        'icon': 'fa-solid fa-screwdriver-wrench',
        'job_type': 'bad_rules_retry',
        'target_picker': 'none',
        # What "Edit" of a bad rule does by hand, for every bad rule: YARA "undefined
        # identifier X" where X is another rule — imported linked to it (several if needed),
        # like relink_rules; any format — validated again as it is (fixed validators, rules
        # imported since). Imports for the bad rule's owner; never edits a rule's text.
        'extra_options': [
            {'key': 'formats', 'type': 'multiselect', 'label': 'Formats (none checked = every format)',
             'options': [{'value': 'yara', 'label': 'YARA — undefined identifier: link the rule it names'},
                         {'value': 'kunai', 'label': 'Kunai'},
                         {'value': 'wazuh', 'label': 'Wazuh'},
                         {'value': 'sigma', 'label': 'Sigma'},
                         {'value': 'suricata', 'label': 'Suricata'},
                         {'value': 'splunk', 'label': 'Splunk'},
                         {'value': 'kql', 'label': 'KQL'}],
             'default': ['yara']},
            {'key': 'link_dependencies', 'type': 'bool', 'label': 'YARA: link the rules a condition names', 'default': True},
            {'key': 'source', 'type': 'text', 'label': 'Only bad rules from this repository URL (optional)', 'default': ''},
        ],
    },
    'disabled_upstream_rules': {
        'label': 'Suricata / Sagan — rules commented out upstream (to the trash)',
        'icon': 'fa-solid fa-comment-slash',
        'job_type': 'disabled_upstream_rules',
        'target_picker': 'none',
        # Issue #62: rules a ruleset ships disabled ("# alert …", e.g. ET Open's costly ones) but imported
        # as active before the importers skipped them. Git rules: their file is read again; uploads
        # (ZIP): compared with reference rulesets by sid + msg. Dry run by default; trash = restorable.
        'extra_options': [
            {'key': 'dry_run', 'type': 'bool', 'label': 'Dry run — only report what would go to the trash', 'default': True},
            {'key': 'formats', 'type': 'multiselect', 'label': 'Formats',
             'options': [{'value': 'suricata', 'label': 'Suricata'}, {'value': 'sagan', 'label': 'Sagan'}],
             'default': ['suricata', 'sagan']},
            {'key': 'source', 'type': 'text', 'label': 'Only rules from this source (optional)', 'default': ''},
            {'key': 'reference_urls', 'type': 'textarea', 'label': 'Reference rulesets for uploaded rules (one URL a line)',
             'default': 'https://rules.emergingthreats.net/open/suricata-7.0/emerging-all.rules'},
        ],
    },
    'reparse_rule_metadata': {
        'label': 'References & metadata — read them again from every rule (platforms, TLP / PAP…)',
        'icon': 'fa-solid fa-book-open',
        'job_type': 'reparse_rule_metadata',
        'target_picker': 'format_filter_only',
        'format_key': 'formats',
    },
    'github_sync_schedule_launch': {
        'label': 'Git updates — run a sync schedule now',
        'icon': 'fa-solid fa-rotate',
        'job_type': 'github_sync_schedule_launch',
        'target_picker': 'none',
        # one of the schedules made on Git Sources → Sync schedules (its repositories, its
        # accept / add-new-rules choices); the options are filled in by serialize_task_types()
        'extra_options': [
            {'key': 'schedule_uuid', 'type': 'select', 'label': 'Sync schedule', 'options_from': 'github_sync_schedules'},
        ],
        'required_options': ['schedule_uuid'],
    },
    'submodules_update': {
        'label': 'Data sources — update MISP taxonomies / galaxies and MITRE CTI',
        'icon': 'fa-solid fa-code-branch',
        'job_type': 'submodules_update',
        'target_picker': 'none',
        # data submodules only (job_handlers.DATA_SUBMODULES) — never Rulezet's code
        'extra_options': [
            {'key': 'names', 'type': 'multiselect', 'label': 'Data sources',
             'options': [{'value': 'misp-taxonomies', 'label': 'MISP taxonomies'},
                         {'value': 'misp-galaxy', 'label': 'MISP galaxies'},
                         {'value': 'cti', 'label': 'MITRE CTI (ATT&CK — large)'}],
             'default': ['misp-taxonomies', 'misp-galaxy']},
        ],
        'required_options': ['names'],
    },
    'action_email': {
        'label': 'Action — Send an email',
        'icon': 'fa-solid fa-envelope',
        'job_type': 'action_email',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'to', 'type': 'text', 'label': 'To (comma-separated, optional)', 'default': ''},
            {'key': 'to_workflow_recipients', 'type': 'bool', 'label': "Also to the workflow's alert recipients", 'default': True},
            {'key': 'subject', 'type': 'text', 'label': 'Subject', 'default': '[Rulezet] {workflow}: {status}'},
            {'key': 'message', 'type': 'textarea', 'label': 'Message', 'variables': True,
             'default': 'The workflow "{workflow}" reached "{task}" on {date} at {time}.\nSo far: {status}.\nFailed: {failed_tasks}.\n{link}'},
        ],
        'required_options': ['subject'],
    },
    'action_notify': {
        'label': 'Action — Notify the admins',
        'icon': 'fa-solid fa-bell',
        'job_type': 'action_notify',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'title', 'type': 'text', 'label': 'Title', 'default': '{workflow}: {status}'},
            {'key': 'message', 'type': 'textarea', 'label': 'Message', 'variables': True, 'default': 'Failed: {failed_tasks}.'},
            {'key': 'only_editor', 'type': 'bool', 'label': "Only the workflow's editor", 'default': False},
        ],
        'required_options': ['title'],
    },
    'action_log': {
        'label': 'Action — Write to the activity log',
        'icon': 'fa-solid fa-pen-to-square',
        'job_type': 'action_log',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'message', 'type': 'textarea', 'label': 'Text', 'variables': True,
             'default': 'Workflow "{workflow}" went well: {done_tasks}.'},
        ],
        'required_options': ['message'],
    },
    'action_webhook': {
        'label': 'Action — Call a webhook (Slack, Mattermost, Teams…)',
        'icon': 'fa-solid fa-paper-plane',
        'job_type': 'action_webhook',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'url', 'type': 'text', 'label': 'Webhook URL (https, public)', 'default': ''},
            {'key': 'message', 'type': 'textarea', 'label': 'Message ("text" of the JSON sent)', 'variables': True,
             'default': ':gear: {workflow} — {task}: {status}. Failed: {failed_tasks}. {link}'},
        ],
        'required_options': ['url'],
    },
    'action_check': {
        'label': 'Check — a figure (go on only if…)',
        'icon': 'fa-solid fa-code-branch',
        'job_type': 'action_check',
        'target_picker': 'none',
        'extra_options': [
            {'key': 'metric', 'type': 'select', 'label': 'Figure', 'default': 'bad_rules',
             'options': [{'value': k, 'label': v[0]} for k, v in _FIGURES.items()]},
            {'key': 'operator', 'type': 'select', 'label': 'Condition', 'default': 'gt',
             'options': [{'value': k, 'label': v[0]} for k, v in _OPERATORS.items()]},
            {'key': 'value', 'type': 'text', 'label': 'Value (a whole number)', 'default': '0'},
        ],
        'required_options': ['metric', 'operator', 'value'],
    },
    'clear_caches': {
        'label': 'Caches — clear them (home figures, stats, pages)',
        'icon': 'fa-solid fa-broom',
        'job_type': 'clear_caches',
        'target_picker': 'none',
    },
    'git_cache_pull': {
        'label': 'Git clone cache — pull every kept clone',
        'icon': 'fa-solid fa-code-pull-request',
        'job_type': 'git_cache_pull',
        'target_picker': 'none',
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


def _with_options(opt):
    """An extra option whose choices come from the database ('options_from'), filled in now."""
    if opt.get('options_from') == 'github_sync_schedules':
        from app.core.db_class.git import GithubSyncSchedule
        opts = [{'value': s.uuid, 'label': s.title + ('' if s.is_active else ' (paused)')}
                for s in GithubSyncSchedule.query.order_by(GithubSyncSchedule.title).all()]
        return {**opt, 'options': opts}
    return opt


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
            'extra_options': [_with_options(o) for o in t.get('extra_options', [])],
            'required_options': t.get('required_options', []),
            'description': t.get('description', ''),
        }
        for key, t in TASK_TYPES.items()
    }


# What happens when the task runs — shown on hover of its card and under the chosen type in the
# task window (task_scheduler.html), so an admin knows what they are about to schedule.
_DESCRIPTIONS = {
    'quality_score': 'Scores every targeted rule (documentation, traceability, validity) and stores it; the rules list and rule pages show the new score.',
    'attack_parser': 'Reads MITRE ATT&CK technique ids in the targeted rules and links them; ATT&CK pages and filters are updated.',
    'misp_update_data': 'Pulls the latest version of the MISP taxonomies and galaxies already imported; new tags appear, existing ones keep their links.',
    'misp_import_all_taxonomies': 'Imports every MISP taxonomy not yet on this instance as tags.',
    'misp_import_all_galaxies': 'Imports every MISP galaxy not yet on this instance (threat actors, tools…).',
    'attack_update_data': 'Downloads the latest MITRE ATT&CK data (techniques, tactics, names); technique pages use it right away.',
    'db_backup': 'Dumps the PostgreSQL database to the backup folder; nothing else changes.',
    'rule_validation_run': 'Runs the false-positive gate on the rules changed since the last run (or all of them with Full scan) and records the results.',
    'activity_log_purge': 'Deletes old activity log entries (optionally only some actions); the rest of the log is kept.',
    'connector_pull': 'Pulls rules from one federation connector (another Rulezet instance) and imports or updates them.',
    'github_repo_resync': 'Rebuilds the Git Sources registry (repositories, rule counts, branches) from the rules in the database.',
    'relink_rules': 'Looks again for links between rules already imported (Wazuh parents, Kunai shared hashes, YARA rules a condition names) and adds the missing ones.',
    'bad_rules_retry': 'Tries every bad rule again: YARA rules naming another rule are imported linked to it, any rule now valid is imported for its owner, the others get a fresh error message.',
    'reparse_rule_metadata': 'Reads references, platforms, TLP / PAP and the other metadata again from each rule\'s text; tags and filters follow. Clear the caches after to see new figures on the home page.',
    'git_cache_pull': 'Runs git pull on every repository clone kept on the server, so the next import or update reads the latest files.',
    'rule_git_mirror_sync': 'Pushes the rules of each Rulesets mirror to its git repository (one commit per sync).',
    'native_tags_import': 'Reads the tags written inside each rule (its own format\'s tag field) and attaches them as Rulezet tags.',
    'platform_tagging': 'Applies a saved platform-tag config: rules matching its patterns get the platform tags (Windows, Linux…).',
    'field_parser': 'Applies a saved field-parser config to re-read rule fields (CVE ids and the others it lists).',
    'github_import': 'Imports the rules of one git repository (any host); new rules are created, bad ones go to Bad rules.',
    'github_branch_backfill': 'Fills in the git branch of rules imported before branches were recorded.',
    'suricata_audit': 'Checks Suricata rules and writes a report; no rule is changed.',
    'suricata_deep_validate': 'Validates Suricata rules with the real Suricata engine, a batch per run, and records the result.',
    'gamification_recompute': 'Recomputes every user\'s points, level and badges; the leaderboard cache is reset at the end.',
    'github_sync_schedule_launch': 'Runs one Git sync schedule now: checks its repositories for updated and new rules, then accepts / adds them if the schedule says so — the same as its own timer.',
    'submodules_update': 'Pulls the latest MISP taxonomies / galaxies (and MITRE CTI if chosen) from their git repositories; run the MISP / ATT&CK update tasks after it to load them.',
    'action_email': 'Sends an email to the addresses given and/or the workflow\'s alert recipients; subject and message take {variables} (workflow, status, failed tasks, link…). Chain it after a task with "If it fails" or "If it succeeds".',
    'action_notify': 'Puts a notification in the bell of every admin (or of the workflow\'s editor); title and message take {variables}.',
    'action_log': 'Writes a line in the activity log (Admin → Logs) — e.g. "went well" after the last task; the text takes {variables}.',
    'action_webhook': 'POSTs a JSON message ({"text": …}) to a public https URL: a Slack / Mattermost / Teams incoming webhook or any service. Private and local addresses are refused.',
    'action_check': 'A gate: counts a figure of the instance (bad rules, rules created today, failed jobs…) and succeeds only if the condition holds. Chain "If it succeeds" for one road and "If it fails" for the other — e.g. bad rules > 50 → Bad rules retry, else nothing.',
    'db_backup_rotate': 'Makes a new backup, checks it (pg_restore can read it), then deletes the oldest automatic backups (rulezet_<date>.dump) so N remain — never fewer than 3, never the new one, never a dump named by hand. If anything fails, nothing is deleted and every admin is alerted.',
    'repo_quality': 'Scores every Git source 0-100 from its rules: their average quality score, imports that failed (bad rules), valid and licensed rules, last sync, conflicts. Shown in Git Sources and on each source. Run it after Rule Quality Score.',
    'clear_caches': 'Empties the caches (home figures, ATT&CK / CVE stats, cached pages, leaderboard) so what the workflow changed shows right away. Put it last.',
    'ai_rule_analysis': 'Asks the AI agent to write an analysis report for rules that have none (a batch per run), published or kept private.',
}
for _key, _text in _DESCRIPTIONS.items():
    if _key in TASK_TYPES:
        TASK_TYPES[_key].setdefault('description', _text)
