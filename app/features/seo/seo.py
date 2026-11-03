"""
seo.py — /robots.txt, /sitemap.xml (an index) and /sitemap-<section>-<n>.xml, plus the template values of
every page (default title / description / keywords, noindex, structured data). Logic in seo_core.py,
values in the setting seo (app/config/seo.json).
"""
import math
from xml.sax.saxutils import escape

from flask import Blueprint, Response, abort, request

from app import cache
from app.features.seo import seo_core as SEO

seo_blueprint = Blueprint('seo', __name__)

CACHE_SECONDS = 3600


def _base():
    return request.url_root.rstrip('/')


@seo_blueprint.app_context_processor
def _seo_context():
    conf = SEO.conf()
    return {'seo': {'indexable': SEO.indexable(), 'title': conf.get('title') or 'Rulezet',
                    'description': conf.get('description') or '', 'keywords': ', '.join(conf.get('keywords') or [])},
            'seo_site_jsonld': lambda: SEO.site_jsonld(_base()),
            'seo_rule_jsonld': lambda rule: SEO.rule_jsonld(rule, _base())}


@seo_blueprint.route('/robots.txt')
def robots():
    lines = ['User-agent: *']
    if not SEO.indexable():
        lines.append('Disallow: /')                    # a self-hosted copy: leave the results to rulezet.org
    else:
        lines += [f'Disallow: {p}' for p in (SEO.conf().get('disallow') or [])]
        lines += ['Allow: /', '', f'Sitemap: {_base()}/sitemap.xml']
    return Response('\n'.join(lines) + '\n', mimetype='text/plain',
                    headers={'Cache-Control': f'public, max-age={CACHE_SECONDS}'})


def _xml(body):
    return Response('<?xml version="1.0" encoding="UTF-8"?>\n' + body, mimetype='application/xml',
                    headers={'Cache-Control': f'public, max-age={CACHE_SECONDS}'})


@seo_blueprint.route('/sitemap.xml')
@cache.cached(timeout=CACHE_SECONDS, query_string=True)
def sitemap_index():
    if not SEO.indexable():
        abort(404)
    base, size = _base(), SEO.page_size()
    parts = []
    for section in SEO.SECTIONS:
        n = SEO.count(section)
        for page in range(1, max(1, math.ceil(n / size)) + 1 if n else 1):
            parts.append(f'  <sitemap><loc>{escape(f"{base}/sitemap-{section}-{page}.xml")}</loc></sitemap>')
    return _xml('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(parts) + '\n</sitemapindex>\n')


@seo_blueprint.route('/sitemap-<section>-<int:page>.xml')
@cache.cached(timeout=CACHE_SECONDS, query_string=True)
def sitemap_part(section, page):
    if not SEO.indexable() or section not in SEO.SECTIONS or page < 1:
        abort(404)
    rows = []
    for loc, lastmod, changefreq, priority in SEO.urls(section, page, _base()):
        row = f'  <url><loc>{escape(loc)}</loc>'
        if lastmod:
            row += f'<lastmod>{lastmod}</lastmod>'
        if changefreq:
            row += f'<changefreq>{changefreq}</changefreq>'
        if priority is not None:
            row += f'<priority>{float(priority):.1f}</priority>'
        rows.append(row + '</url>')
    if not rows and page > 1:
        abort(404)
    return _xml('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(rows) + '\n</urlset>\n')
