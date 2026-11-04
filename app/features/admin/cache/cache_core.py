"""Admin → Cache: what the cache is, how well it works, and the admin's actions on it
(docs/future/caching.md). Every action is logged (cache.*)."""
from flask import current_app

from app.core.utils import cache_versions, page_cache

SETTINGS = ('cache.enabled', 'cache.rule_page_seconds', 'cache.rule_parts_seconds', 'cache.api_seconds',
            'cache.user_activity_seconds')


def backend():
    """{'type', 'shared', 'ok', 'detail'} of the shared cache."""
    from app import cache
    try:
        t = type(cache.cache).__name__          # the backend really in use (Redis falls back to files if down)
    except Exception:
        t = current_app.config.get('CACHE_TYPE', '')
    info = {'type': t, 'shared': t in ('RedisCache', 'FileSystemCache'), 'ok': True, 'detail': ''}
    if t == 'RedisCache':
        try:
            import redis
            r = redis.Redis.from_url(current_app.config.get('CACHE_REDIS_URL') or 'redis://localhost:6379/0',
                                     socket_connect_timeout=1)
            mem = r.info('memory')
            info['detail'] = f"{r.dbsize()} keys, {mem.get('used_memory_human', '?')} used"
        except Exception as e:
            info['ok'], info['detail'] = False, f'Redis unreachable: {e.__class__.__name__}'
    elif t == 'FileSystemCache':
        info['detail'] = current_app.config.get('CACHE_DIR', '')
    elif t in ('SimpleCache', 'NullCache'):
        info['detail'] = 'one per process (site, API and worker do not share it)' if t == 'SimpleCache' else 'caching disabled'
    return info


def status():
    from app.core.utils.app_settings import get_setting
    return {
        'backend': backend(),
        'memory_backend': current_app.config.get('MEMORY_CACHE_TYPE', ''),
        'settings': {k: get_setting(k) for k in SETTINGS},
        'stats': page_cache.stats(),
        'code_version': cache_versions.code_version(),
        'generations': {'rules': cache_versions.global_gen(), 'bulk': cache_versions.bulk_gen()},
    }


def refresh_all_rules():
    """Every rule page, part and list gets a new key (old entries expire on their own)."""
    cache_versions.bump_all()


def refresh_rule(rule_id):
    from app.features.rule.rule_core import _active
    from app.core.db_class.rule import Rule
    if not _active().filter(Rule.id == int(rule_id)).first():
        return False
    cache_versions.bump_rule(int(rule_id))
    return True


def clear_all():
    """Empties both caches (also the generations: they come back as new values)."""
    from app import cache, memory_cache
    cache.clear()
    memory_cache.clear()


def warm_rules(limit=200, base_url=None):
    """Renders the `limit` most voted rule pages as an anonymous visitor, so the first real visitors
    (and crawlers) get them from the cache. base_url: the public address (INSTANCE_PUBLIC_URL) — the
    cache key holds the host, a page warmed for another host would never be read.
    Returns (done, failed)."""
    from app.features.rule.rule_core import _active
    from app.core.db_class.rule import Rule
    limit = max(1, min(int(limit or 200), 5000))
    base_url = (base_url or current_app.config.get('INSTANCE_PUBLIC_URL') or '').rstrip('/') or None
    ids = [r.id for r in _active().order_by(Rule.vote_up.desc().nullslast(), Rule.id.desc()).limit(limit).all()]
    client = current_app.test_client()
    done = failed = 0
    for rid in ids:
        kw = {'base_url': base_url} if base_url else {}
        try:
            r = client.get(f'/rule/detail_rule/{rid}', **kw)
            done, failed = (done + 1, failed) if r.status_code == 200 else (done, failed + 1)
        except Exception:
            failed += 1
    return done, failed
