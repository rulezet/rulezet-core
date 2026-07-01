_registry: dict = {}   # format_name (lowercase) → driver class


def register_driver(format_name: str):
    def decorator(cls):
        _registry[format_name.lower()] = cls
        return cls
    return decorator


def get_driver(format_name: str):
    cls = _registry.get((format_name or '').lower())
    return cls() if cls else None


def list_supported_formats() -> list:
    return list(_registry.keys())


def get_all_capabilities() -> list:
    return [cls().get_capabilities() for cls in _registry.values()]
