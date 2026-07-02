import re

import yaml

SUPPORTED_FORMATS = ('yara', 'sigma')


class _BlockDumper(yaml.SafeDumper):
    pass


def _str_representer(dumper, data):
    style = '|' if '\n' in data else None
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style=style)


_BlockDumper.add_representer(str, _str_representer)


def _slug(title: str) -> str:
    slug = re.sub(r'[^A-Za-z0-9]+', '', (title or '').title())
    return slug or 'Rule'


def _artifact_name(rule) -> str:
    fmt_label = 'YARA' if rule.format.lower() == 'yara' else 'Sigma'
    return f"Rulezet.Detection.{fmt_label}.{_slug(rule.title)}"


def _description(rule, base_url: str) -> str:
    tags = ', '.join(assoc.tag.name for assoc in rule.rule_tags_assocs if assoc.tag)
    lines = [
        f"{rule.format.upper()} rule from Rulezet: \"{rule.title}\"",
        f"Rule UUID: {rule.uuid}",
        f"Source: {base_url.rstrip('/')}/rule/detail_rule/{rule.uuid}",
    ]
    if rule.author:
        lines.append(f"Author: {rule.author}")
    if tags:
        lines.append(f"Tags: {tags}")
    return '\n'.join(lines) + '\n'


def _yara_artifact(rule, base_url: str) -> dict:
    return {
        'name': _artifact_name(rule),
        'description': _description(rule, base_url),
        'type': 'CLIENT',
        'parameters': [
            {
                'name': 'YaraRule',
                'description': 'YARA rule content (pre-filled from Rulezet)',
                'default': rule.to_string,
            },
            {'name': 'ScanProcesses', 'type': 'bool', 'default': 'true'},
            {'name': 'ScanDisk', 'type': 'bool', 'default': 'false'},
        ],
        'sources': [
            {
                'name': 'ProcessScan',
                'query': (
                    'SELECT Pid, Name, Exe,\n'
                    '       Rule, Meta, Strings\n'
                    'FROM proc_yara(rules=YaraRule, pid=Pid)\n'
                    'FROM pslist()\n'
                    'WHERE ScanProcesses\n'
                ),
            },
            {
                'name': 'DiskScan',
                'query': (
                    'SELECT OSPath, Rule, Meta, Strings\n'
                    'FROM yara(rules=YaraRule, files="C:/**")\n'
                    'WHERE ScanDisk\n'
                ),
            },
        ],
    }


def _sigma_artifact(rule, base_url: str) -> dict:
    return {
        'name': _artifact_name(rule),
        'description': _description(rule, base_url),
        'type': 'CLIENT_EVENT',
        'parameters': [
            {
                'name': 'SigmaRule',
                'description': 'Sigma rule content (pre-filled from Rulezet)',
                'default': rule.to_string,
            },
        ],
        'sources': [
            {
                'query': (
                    'SELECT * FROM sigma(\n'
                    '  rules=[SigmaRule],\n'
                    '  log_sources=dict(\n'
                    '    `windows/process_creation`={\n'
                    '      SELECT * FROM watch_etw(guid="{f4e1897c-bb5d-5668-f1d8-040f4d8dd344}")\n'
                    '    }\n'
                    '  )\n'
                    ')\n'
                ),
            },
        ],
    }


def generate_velociraptor_artifact(rule, base_url: str = 'https://rulezet.org') -> str:
    """Generate a Velociraptor Artifact YAML string for a YARA or Sigma rule."""
    fmt = (rule.format or '').lower()
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Velociraptor export is not supported for format '{rule.format}'")

    artifact = _yara_artifact(rule, base_url) if fmt == 'yara' else _sigma_artifact(rule, base_url)
    return yaml.dump(artifact, Dumper=_BlockDumper, sort_keys=False, allow_unicode=True, default_flow_style=False)
