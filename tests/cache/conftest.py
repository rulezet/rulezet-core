import pytest


@pytest.fixture
def real_cache(app):
    """The tests run with NullCache; these ones need a cache that keeps values."""
    from app import cache, memory_cache
    cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})
    memory_cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 60})
    with app.app_context():
        cache.clear()
        memory_cache.clear()
    yield cache
    cache.init_app(app, config={'CACHE_TYPE': 'NullCache'})
    memory_cache.init_app(app, config={'CACHE_TYPE': 'NullCache'})
