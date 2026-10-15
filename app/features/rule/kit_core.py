"""kit_core.py — what a "kit" page does with a set of rules, whatever the
subject (a vulnerability: features/vulnerability, an ATT&CK technique:
features/attack): coverage per format against the formats expected, stats for
the charts, a zip of every rule, a bundle made of them.
"""
import datetime
import io
import re
import zipfile

from app import db

_SAFE = re.compile(r'[^A-Za-z0-9._-]+')


def format_coverage(rules: list, expected_formats, with_stats: bool = False) -> dict:
    """Rules grouped per format, the expected ones first (covered or not),
    then any other format that has rules, and the gaps. with_stats=True adds
    what the charts read ({categories, series} for ChartViewer) — only
    computed when the page's Coverage card is opened."""
    by_format, by_month, by_author = {}, {}, {}
    for r in rules:
        fmt = (r.format or 'no format').strip().lower()
        by_format.setdefault(fmt, []).append(r.id)
        if not with_stats:
            continue
        if r.creation_date:
            month = r.creation_date.strftime('%Y-%m')
            by_month[month] = by_month.get(month, 0) + 1
        author = (r.author or 'Unknown').strip()[:60] or 'Unknown'
        by_author[author] = by_author.get(author, 0) + 1

    expected = [str(f).lower() for f in expected_formats]
    formats = [{'format': f, 'count': len(by_format.get(f, [])), 'expected': True} for f in expected]
    formats += [{'format': f, 'count': len(v), 'expected': False}
                for f, v in sorted(by_format.items(), key=lambda kv: -len(kv[1])) if f not in expected]

    covered_expected = [f for f in formats if f['expected'] and f['count']]
    top_authors = sorted(by_author.items(), key=lambda kv: -kv[1])[:8]
    months = sorted(by_month)
    result = {
        'formats': formats,
        'covered_formats': [f['format'] for f in formats if f['count']],
        'gaps': [f['format'] for f in formats if f['expected'] and not f['count']],
        'covered_expected': len(covered_expected),
        'expected_total': len(expected),
    }
    if with_stats:
        result['stats'] = {
            'coverage_pct': round(100 * len(covered_expected) / len(expected)) if expected else 0,
            'covered_expected': len(covered_expected),
            'expected_total': len(expected),
            'by_format': {'categories': [f['format'] for f in formats if f['count']],
                          'series': [{'name': 'Rules', 'values': [f['count'] for f in formats if f['count']]}]},
            'timeline': {'categories': months,
                         'series': [{'name': 'Rules added', 'values': [by_month[m] for m in months]}]},
            'authors': {'categories': [a for a, _ in top_authors],
                        'series': [{'name': 'Rules', 'values': [n for _, n in top_authors]}]},
        }
    return result


def zip_rules(rules: list, readme_title: str, readme_lines: list) -> io.BytesIO:
    """Every rule, one folder per format, plus a README."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        used = set()
        for r in rules:
            fmt = _SAFE.sub('_', (r.format or 'no_format').lower())
            name = _SAFE.sub('_', r.title or r.uuid).strip('_')[:80] or r.uuid
            ext = r.get_extension() if hasattr(r, 'get_extension') else 'txt'
            path = f'{fmt}/{name}.{ext}'
            if path in used:
                path = f'{fmt}/{name}-{r.uuid[:8]}.{ext}'
            used.add(path)
            archive.writestr(path, r.to_string or '')
        readme = [f'# {readme_title}', ''] + list(readme_lines) + [
            f"Generated {datetime.datetime.now(tz=datetime.timezone.utc):%Y-%m-%d %H:%M} UTC"]
        archive.writestr('README.md', '\n'.join(readme) + '\n')
    buffer.seek(0)
    return buffer


def visible_bundles_filter():
    """Bundles a kit page may list: public ones, plus the viewer's own
    private ones — never another user's private bundle."""
    from flask_login import current_user
    from sqlalchemy import or_, and_
    from app.core.db_class.bundle import Bundle
    if current_user.is_authenticated:
        return or_(Bundle.access == True, and_(Bundle.access == False, Bundle.user_id == current_user.id))  # noqa: E712
    return Bundle.access == True  # noqa: E712


def bundle_from_rules(name: str, description: str, rules: list, user, vulnerability_ids=None, public: bool = True):
    """A bundle owned by *user* with *rules*, one folder per format — public,
    or private (only the owner sees it) when public=False.
    The name gets " (2)", " (3)"… if the user already has one with it."""
    from app.features.bundle import bundle_core as BundleModel
    final_name, n = name, 2
    while BundleModel.bundle_name_taken(final_name, user.id):
        final_name = f'{name} ({n})'
        n += 1
    bundle = BundleModel.create_bundle({
        'name': final_name, 'description': description, 'public': bool(public),
        'vulnerability_identifiers': list(vulnerability_ids or []),
    }, user)
    # Folders first (one per format), then the rules: add_rules_to_bundle only
    # files the rules that have no place in the tree yet into "Unsorted".
    for fmt in sorted({(r.format or 'no format').lower() for r in rules}):
        BundleModel.place_rules_in_structure(bundle.id, [r.id for r in rules if (r.format or 'no format').lower() == fmt], fmt)
    db.session.commit()
    BundleModel.add_rules_to_bundle(bundle.id, [r.id for r in rules])
    return bundle
