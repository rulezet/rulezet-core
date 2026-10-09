"""Pivograph document for the graph view of the "Rule formats" page.

Rulezet sits in the middle, every rule format around it, and behind each
format its own outputs (what Rulezet can turn its rules into). Which output is
offered for which format mirrors the rule detail page and /rule/download_rule:

- JSON, MISP object, MISP event and STIX 2.1: every format
  (app/features/misp/rule/misp_object.py has a dedicated MISP template for
  most formats and a generic object for the others; STIX is converted from
  the MISP event)
- Velociraptor artifact: exporters/velociraptor_exporter.SUPPORTED_FORMATS
- Splunk / Elastic / Sentinel / Sumo Logic / SecOps / Loki queries: Sigma
  only (exporters/sigma_convert_exporter.SIGMA_CONVERT_TARGETS)
- suricata-update feed: Suricata only (/rule/feed/suricata.rules)

Format of the document: https://github.com/ecrou-exact/project-graph
(app/modules/pivograph, docs/content/03-format.md). Images are embedded as
data: URLs so the iframe never fetches from the site and the app's PNG/PDF
exports keep the logos.
"""
import base64
import math
import mimetypes
import os
from urllib.parse import quote

from flask import current_app

from ..exporters.sigma_convert_exporter import SIGMA_CONVERT_TARGETS
from ..exporters.velociraptor_exporter import SUPPORTED_FORMATS as VELOCIRAPTOR_FORMATS

# Formats with a dedicated MISP object template (else a generic object).
MISP_TEMPLATE_FORMATS = {'yara', 'sigma', 'suricata', 'wazuh', 'nse', 'crs', 'nova',
                         'splunk', 'elastic', 'kql', 'kunai'}

# Outputs every format gets.
COMMON_OUTPUTS = [
    {'id': 'out-json', 'label': 'JSON', 'icon': 'custom-icon/json.svg',
     'description': 'Rulezet JSON: the rule and its metadata, re-importable as is.'},
    {'id': 'out-misp-object', 'label': 'MISP object', 'icon': 'custom-icon/misp.svg',
     'description': 'The rule as a MISP object, ready to import into a MISP instance.'},
    {'id': 'out-misp-event', 'label': 'MISP event', 'icon': 'custom-icon/misp.svg',
     'description': 'A MISP event holding the rule object and its tags.'},
    {'id': 'out-stix', 'label': 'STIX 2.1', 'icon': 'custom-icon/logo_stix.svg',
     'description': 'STIX 2.1 bundle, converted from the MISP event.'},
]

# Official site of each output (node `url`: opened by a double-click on the node).
OUTPUT_URLS = {
    'misp-object': 'https://www.misp-project.org/objects.html',
    'misp-event': 'https://www.misp-project.org/',
    'stix': 'https://oasis-open.github.io/cti-documentation/',
    'velociraptor': 'https://docs.velociraptor.app/',
    'sigma-splunk': 'https://www.splunk.com/',
    'sigma-elastic': 'https://www.elastic.co/security',
    'sigma-sentinel': 'https://learn.microsoft.com/en-us/azure/sentinel/',
    'sigma-sumologic': 'https://www.sumologic.com/',
    'sigma-secops': 'https://cloud.google.com/security/products/security-operations',
    'sigma-loki': 'https://grafana.com/oss/loki/',
    'suricata-feed': 'https://docs.suricata.io/en/latest/rule-management/suricata-update.html',
}

SIGMA_TARGET_ICONS = {
    'splunk': 'custom-icon/splunk.png', 'elastic': 'custom-icon/elastic.svg',
    'sentinel': 'custom-icon/sentinel.svg', 'sumologic': 'custom-icon/sumologic.svg',
    'secops': 'custom-icon/secops.svg', 'loki': 'custom-icon/loki.svg',
}


def _data_url(static_path: str):
    """A file under static/ as a data: URL (None if missing)."""
    path = os.path.join(current_app.static_folder, static_path)
    if not os.path.isfile(path):
        return None
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    with open(path, 'rb') as fp:
        return f'data:{mime};base64,{base64.b64encode(fp.read()).decode()}'


def _format_outputs(key: str) -> list:
    """The outputs Rulezet offers for one format: (suffix, label, icon, description, specific)."""
    outs = [(o['id'][4:], o['label'], o['icon'], o['description'], False) for o in COMMON_OUTPUTS]
    if key in VELOCIRAPTOR_FORMATS:
        outs.append(('velociraptor', 'Velociraptor', 'custom-icon/velociraptor-remove-bg.png',
                     'A ready-to-deploy Velociraptor artifact (YAML) running the rule on endpoints.', True))
    if key == 'sigma':
        for target, meta in SIGMA_CONVERT_TARGETS.items():
            outs.append((f'sigma-{target}', meta['label'], SIGMA_TARGET_ICONS.get(target, 'custom-icon/json.svg'),
                         f'Sigma rule converted with pySigma into a {meta["label"]} query.', True))
    if key == 'suricata':
        outs.append(('suricata-feed', 'suricata-update feed', 'images/formats/suricata.png',
                     'Every Suricata rule as one feed for suricata-update (/rule/feed/suricata.rules).', True))
    return outs


# Fixed radial layout (meta.fixedLayout): Rulezet at the centre, the formats on
# an inner ring, their outputs on an outer ring. Each format owns a slice of the
# circle proportional to its number of outputs, and its outputs stay inside
# that slice (on two alternating radii, so long names don't touch) — branches
# never overlap or cross.
FORMAT_RING  = 700
OUTPUT_RINGS = (1250, 1450)

# Shared look: no outline, no background — just the logo and the name.
_PLAIN = {'color': 'transparent', 'borderWidth': 0, 'imageFit': 'contain',
          'labelBackground': 'none', 'labelFont': 'sans'}


def build_formats_graph(formats: list, base_url: str) -> dict:
    """`formats` as returned by rule_core.get_formats_overview().

    Every format gets its own output nodes (its JSON, its MISP event…), not
    nodes shared by all formats: one branch per format. Each node carries
    the format's name as a tag, so the side panel's Tags list filters the
    graph down to one format's branch. Output icons live on one node type
    per kind of output, so each image is embedded once.
    """
    base_url = base_url.rstrip('/')
    shown = [(f, _format_outputs(f['key'])) for f in formats if f['key'] != 'no format']
    total_outputs = sum(len(outs) for _, outs in shown) or 1

    node_types = {
        'rulezet': {**_PLAIN, 'label': 'Rulezet', 'shape': 'circle', 'size': 80, 'labelSize': 20},
        'format':  {**_PLAIN, 'label': 'Rule format', 'shape': 'circle', 'size': 44, 'labelSize': 15},
    }
    nodes = [{
        'id': 'rulezet', 'label': 'Rulezet', 'type': 'rulezet', 'x': 0, 'y': 0,
        'image': _data_url('images/formats/rulezet.png'),
        'description': 'Community platform for detection rules: every format around is hosted, '
                       'validated and exported by Rulezet.',
        'url': base_url + '/',
        'links': [{'label': 'Rule formats', 'url': f'{base_url}/rule/formats'},
                  {'label': 'Documentation', 'url': f'{base_url}/docs/'},
                  {'label': 'GitHub', 'url': 'https://github.com/rulezet/rulezet-core'}],
    }]
    edges = []

    start = -math.pi / 2                                   # first format at the top
    for f, outs in shown:
        key = f['key']
        slice_ = 2 * math.pi * len(outs) / total_outputs
        angle = start + slice_ / 2
        node_id = f'fmt-{key}'
        card_url = f'{base_url}/rule/formats#{key.replace(" ", "-")}'
        details = {'Rules': f['rule_count'], 'Category': f['category']}
        if f.get('maintainer'):
            details['Maintainer'] = f['maintainer']
        if f.get('extensions'):
            details['Files'] = f['extensions']
        details['MISP template'] = 'dedicated' if key in MISP_TEMPLATE_FORMATS else 'generic'
        node = {
            'id': node_id, 'label': f['title'], 'type': 'format',
            'x': round(FORMAT_RING * math.cos(angle)), 'y': round(FORMAT_RING * math.sin(angle)),
            'description': f['description'],
            # Double-click opens `url`: the official site, else its card here.
            'url': f.get('official_url') or card_url,
            'details': details,
            'tags': [f['title']],
        }
        # Same links as the format's card.
        links = []
        if f.get('official_url'):
            links.append({'label': 'Official site', 'url': f['official_url']})
        if f.get('docs_url'):
            links.append({'label': 'Documentation', 'url': f['docs_url']})
        links.append({'label': f"{f['title']} rules on Rulezet",
                      'url': f'{base_url}/rule/rules_list?rule_type={quote(key)}'})
        links.append({'label': 'Format card on Rulezet', 'url': card_url})
        node['links'] = links
        if f.get('logo'):
            node['image'] = _data_url(f'images/formats/{f["logo"]}')
        nodes.append(node)
        edges.append({'from': 'rulezet', 'to': node_id, 'type': 'hosts',
                      'label': f"{f['rule_count']:,} rules"})

        for j, (suffix, label, icon, description, specific) in enumerate(outs):
            type_key = f'out-{suffix}'
            if type_key not in node_types:
                node_types[type_key] = {**_PLAIN, 'label': label, 'shape': 'square', 'size': 22,
                                        'labelSize': 12, 'image': _data_url(icon)}
            a = start + slice_ * (j + 0.5) / len(outs)
            r = OUTPUT_RINGS[j % 2]
            out = {
                'id': f'{node_id}-{suffix}', 'label': label, 'type': type_key,
                'x': round(r * math.cos(a)), 'y': round(r * math.sin(a)),
                'description': f"{f['title']}: {description}",
                'url': OUTPUT_URLS.get(suffix) or f'{base_url}/api/',
                'tags': [f['title']],
            }
            if suffix.startswith('sigma-'):
                out['links'] = [{'label': 'pySigma (the converter)', 'url': 'https://github.com/SigmaHQ/pySigma'}]
            nodes.append(out)
            edges.append({'from': node_id, 'to': f'{node_id}-{suffix}',
                          'type': 'converts' if specific else 'exports'})
        start += slice_

    return {
        'version': 1,
        'meta': {
            'title': 'Rulezet rule formats',
            'description': 'Rulezet in the middle, the rule formats it hosts around it, and behind each '
                           'format the outputs its rules can be exported or converted to. Grey: exports '
                           'every format has (JSON, MISP, STIX); green: conversions specific to the format. '
                           'Filter by a format in the Tags list to see its branch alone.',
            'fixedLayout': True,
            'readOnly': True,
        },
        'nodeTypes': node_types,
        'edgeTypes': {
            'hosts':    {'label': 'hosts', 'color': '#9ec5fe', 'width': 1.5, 'direction': 'none',
                         'curve': 'straight', 'labelSize': 11, 'labelBackground': 'none'},
            'exports':  {'label': 'exports to', 'color': '#ced4da', 'width': 1, 'direction': 'none',
                         'curve': 'straight', 'hideLabel': True},
            'converts': {'label': 'converts to', 'color': '#63c5b5', 'width': 1.5, 'direction': 'none',
                         'curve': 'straight', 'hideLabel': True},
        },
        'nodes': nodes,
        'edges': edges,
    }
